"""Incident LangChain tools for agent-bmc.

Split out of ``bmc_tools`` (which stays as the thin aggregator + registry) once that
module grew past the repo's 1000-line-per-module limit. Shares the same lazy
``BaseToolHandler`` singleton via ``bmc.libs.tool_handler.get_shared_handler()`` —
deliberately not imported from ``bmc_tools`` itself, to avoid a cyclic import with
the aggregator that registers this module's tools. See ``bmc_work_order_tools.py``
for the full rationale behind the
``too-many-arguments``/``too-many-positional-arguments`` disable below — the same
applies here to ``bmc_create_incident``.
"""

# pylint: disable=too-many-arguments,too-many-positional-arguments
from __future__ import annotations

import logging
from typing import Annotated, Literal

from langchain_core.tools import tool
from pydantic import Field

from agent.internal_tools.ticket_tool_helpers import search_detail_json, work_log_options
from bmc.exceptions.mcp import MCPClientError
from bmc.libs import tool_handler
from bmc.libs.business_defaults import DEFAULT_INCIDENT_ASSIGNED_GROUP
from bmc.libs.constants import (
    AR_FIELD_INCIDENT_ASSIGNED_GROUP,
    AR_FIELD_INCIDENT_NUMBER,
    DEFAULT_WORK_LOG_TYPE,
    INCIDENT_DESCRIPTION_MAX_LENGTH,
    INCIDENT_STATUSES,
    MAX_TICKETS_BY_EMAIL_RESULTS,
)
from bmc.libs.helpers.incident_operations import IncidentOperations
from bmc.libs.tool_handler import BaseToolHandler
from bmc.type_defs.ar_api import ArScalarValue
from bmc.type_defs.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    CloseIncidentInput,
    CreateIncidentInput,
    IncidentNumberInput,
    TicketsByEmailInput,
)
from bmc.type_defs.outputs import (
    IncidentByEmailRow,
    IncidentDetailData,
    IncidentsByEmailData,
)

logger = logging.getLogger(__name__)


def _incident_detail_from_search(
    incident_number: str,
    values_data: dict[str, ArScalarValue],
) -> IncidentDetailData:
    """Build a lean ``IncidentDetailData`` (title/status/assigned group only) from a raw AR values dict."""
    status = values_data.get("Status", "")
    description = values_data.get("Description", "")
    assigned_group = values_data.get(AR_FIELD_INCIDENT_ASSIGNED_GROUP, "")
    return IncidentDetailData(
        incident_number=incident_number,
        status=str(status) if status is not None else "",
        description=str(description) if description is not None else "",
        assigned_group=str(assigned_group) if assigned_group is not None else "",
    )


@tool(
    description=(
        "Create an Incident in BMC Helix ARUS. Only for cases where a matching "
        "categorias-<domain> skill row says Tipo Servicio = Incidente — there is no "
        "generic incident catch-all; anything outside a known domain is always a Work "
        "Order instead, never an incident. Company, Impact and Urgency are fixed and "
        "must not be passed. Fails with no Incident created if reporter_email does not "
        "match a real, already-registered person."
    )
)
async def bmc_create_incident(
    description: Annotated[
        str,
        Field(
            min_length=1,
            max_length=INCIDENT_DESCRIPTION_MAX_LENGTH,
            description=(
                "Short, specific subject line (hard limit: 100 characters — BMC rejects "
                "the whole request above that): which service/system is affected and the "
                'concrete symptom (e.g. "Payroll app down for all users at Medellin '
                'site"), never a generic label like "System not working". Put extra '
                "detail in `detailed_decription` instead of exceeding this limit."
            ),
        ),
    ],
    detailed_decription: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Full incident detail (preserves AR field spelling): who reported it, when it "
                "started, the exact symptom observed, the affected system/application, and "
                "scope (how many users or which site) — enough to diagnose without asking the "
                "user again."
            ),
        ),
    ],
    reporter_email: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Email of the person this incident is filed on behalf of — the real "
                "reporter. Always required, regardless of how it was obtained. Must match "
                "a real, already-registered person; never a fabricated or guessed address."
            ),
        ),
    ],
    product_categorization_tier_1: Annotated[
        str,
        Field(
            min_length=1,
            description="Product categorization tier 1, from the matching categorias-<dominio> skill row.",
        ),
    ],
    product_categorization_tier_2: Annotated[
        str,
        Field(min_length=1, description="Product categorization tier 2, same catalog row."),
    ],
    product_categorization_tier_3: Annotated[
        str,
        Field(min_length=1, description="Product categorization tier 3, same catalog row."),
    ],
    categorization_tier_1: Annotated[
        str,
        Field(description="Operational categorization tier 1, same catalog row."),
    ] = "",
    categorization_tier_2: Annotated[
        str,
        Field(description="Operational categorization tier 2, same catalog row."),
    ] = "",
    assigned_group: Annotated[
        str,
        Field(
            description=(
                "Assigned group, taken from the same catalog row; keep the default only when "
                "the catalog row does not specify one."
            ),
        ),
    ] = DEFAULT_INCIDENT_ASSIGNED_GROUP,
    status: Annotated[
        Literal[INCIDENT_STATUSES],  # type: ignore[valid-type]  # tuple constant expands to Literal values at runtime
        Field(description="Incident status at creation; keep the default unless told otherwise."),
    ] = "Assigned",
    reported_source: Annotated[
        str,
        Field(description="How the incident was reported; keep the default unless told otherwise."),
    ] = "Direct Input",
    service_type: Annotated[
        str,
        Field(description="BMC service type classification; keep the default unless told otherwise."),
    ] = "User Service Restoration",
) -> str:
    """Create an Incident in BMC Helix ARUS (HPD:IncidentInterface_Create).

    Take the category tiers and ``assigned_group`` from a single row of a matching
    ``categorias-<dominio>`` skill (e.g. ``categorias-eventos``, ``categorias-usuario``)
    whose ``Tipo Servicio`` column says ``Incidente`` for this case — there is no
    generic incident catalog: a request outside every known domain is always filed as
    a Work Order instead (see ``bmc_create_work_order``), never guessed as an
    incident. Company, Impact and Urgency are fixed per environment configuration and
    must not be provided by the caller: every incident created here keeps a fixed
    Impact/Urgency (Critical/Extensive), matching the current bmc-mcp behavior. The
    submitter's First/Last Name are resolved from ``reporter_email`` against BMC's
    ``CTM:People`` — this call fails with no Incident created if that person cannot
    be found.

    Parameters
    ----------
    Each parameter is documented on its own ``Annotated``/``Field`` above — not
    repeated here.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded ids on success).
    """
    handler = tool_handler.get_shared_handler()
    data = CreateIncidentInput(
        description=description,
        detailed_decription=detailed_decription,
        reporter_email=reporter_email,
        categorization_tier_1=categorization_tier_1,
        categorization_tier_2=categorization_tier_2,
        product_categorization_tier_1=product_categorization_tier_1,
        product_categorization_tier_2=product_categorization_tier_2,
        product_categorization_tier_3=product_categorization_tier_3,
        assigned_group=assigned_group,
        status=status,
        reported_source=reported_source,
        service_type=service_type,
    )
    result = await IncidentOperations(handler).create(data)
    return result.model_dump_json()


@tool(
    description=(
        "Look up one Incident by its number: title, status and assigned group only — "
        "never the detailed description or notes, which can carry sensitive data. Use "
        "before writing to a ticket, or to confirm the result of a previous write."
    )
)
async def bmc_get_incident(
    incident_number: Annotated[
        str,
        Field(min_length=1, description="Incident Number to look up (e.g. INC000000002106)."),
    ],
) -> str:
    """Read one Incident by its number: title, current status and assigned group.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write. Intentionally does not return the detailed description, notes or
    any other raw BMC field — those can carry sensitive data.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded detail on success).
    """
    handler = tool_handler.get_shared_handler()
    data = IncidentNumberInput(incident_number=incident_number)
    return await search_detail_json(
        handler.client.search_incident(data.incident_number),
        not_found_message=f"Error: No se encontró el incidente {data.incident_number}.",
        build_detail=lambda values: _incident_detail_from_search(data.incident_number, values),
    )


@tool(
    description=(
        "List incidents for one person, searched by the email they used as "
        "reporter_email at creation — not their BMC-resolved login id. One row per "
        "ticket: title, status and assigned group only; capped and flagged if there "
        "are more matches than returned."
    )
)
async def bmc_list_incidents_by_email(
    email: Annotated[
        str,
        Field(min_length=1, description="Requester email, as given to reporter_email at creation."),
    ],
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=MAX_TICKETS_BY_EMAIL_RESULTS,
            description="Maximum number of rows to return; silently capped at this tool's own maximum.",
        ),
    ] = MAX_TICKETS_BY_EMAIL_RESULTS,
) -> str:
    """List incidents reported by one person, searched by their email.

    Matches on the same ``reporter_email`` value passed at creation time — never the
    BMC-resolved login id. Returns one row per ticket with only title, status and
    assigned group — never the detailed description, notes or other raw BMC fields,
    since those can carry sensitive data.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded rows on success).
    """
    handler = tool_handler.get_shared_handler()
    data = TicketsByEmailInput(email=email, limit=limit)
    try:
        result = await handler.client.search_incidents_by_email(data.email)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    total = len(result.entries)
    rows = [
        IncidentByEmailRow(
            incident_number=str(e.values.data.get(AR_FIELD_INCIDENT_NUMBER, "")),
            status=str(e.values.data.get("Status", "")),
            description=str(e.values.data.get("Description", "")),
            assigned_group=str(e.values.data.get(AR_FIELD_INCIDENT_ASSIGNED_GROUP, "")),
        )
        for e in result.entries[: data.limit]
    ]
    out = IncidentsByEmailData(
        email=data.email,
        total_found=total,
        returned=len(rows),
        truncated=total > len(rows),
        incidents=rows,
    )
    logger.info("bmc_list_incidents_by_email ok email=%s total_found=%d", data.email, total)
    return BaseToolHandler.success_toon(out).model_dump_json()


@tool(
    description=(
        "Add a note to an Incident's activity log, visible to whoever reviews the "
        "ticket. Fails if the incident is already closed."
    )
)
async def bmc_add_incident_note(
    incident_number: Annotated[str, Field(min_length=1, description="Target Incident Number.")],
    note_text: Annotated[
        str,
        Field(
            min_length=1,
            description="Text of the note, written as it should be read by whoever reviews the ticket.",
        ),
    ],
    work_log_type: Annotated[
        str,
        Field(description="Category of the note in the ticket activity log; keep the default unless asked otherwise."),
    ] = DEFAULT_WORK_LOG_TYPE,
    view_access: Annotated[
        str,
        Field(description="Visibility of the note in BMC; keep the default unless asked otherwise."),
    ] = "Public",
    secure_work_log: Annotated[
        str,
        Field(description="Whether the note is flagged as secure in BMC; keep the default unless asked otherwise."),
    ] = "No",
) -> str:
    """Add a note to the activity log of an Incident, visible to whoever reviews it.

    Fails if the incident is already closed.

    Returns
    -------
    str
        JSON with ``success`` and confirmation message.
    """
    data = AddIncidentNoteInput(
        incident_number=incident_number,
        **work_log_options(note_text, work_log_type, view_access, secure_work_log),
    )
    result = await IncidentOperations(tool_handler.get_shared_handler()).add_note(data)
    return result.model_dump_json()


@tool(
    description=(
        "Add a note with one file attached to an Incident's activity log. The file "
        "must already exist on the machine running this agent — its content cannot be "
        "sent through this tool. Fails if the incident is already closed."
    )
)
async def bmc_add_incident_attachment(
    incident_number: Annotated[str, Field(min_length=1, description="Target Incident Number.")],
    note_text: Annotated[str, Field(min_length=1, description="Work log detailed description text.")],
    file_path: Annotated[
        str,
        Field(min_length=1, description="Path of the file to attach, as seen by the machine running this agent."),
    ],
    work_log_type: Annotated[
        str,
        Field(description="Category of the note in the ticket activity log; keep the default unless asked otherwise."),
    ] = DEFAULT_WORK_LOG_TYPE,
    view_access: Annotated[
        str,
        Field(description="Visibility of the note in BMC; keep the default unless asked otherwise."),
    ] = "Public",
    secure_work_log: Annotated[
        str,
        Field(description="Whether the note is flagged as secure in BMC; keep the default unless asked otherwise."),
    ] = "No",
) -> str:
    """Add a note with one file attached to the activity log of an Incident.

    The file must already exist on the machine running this agent; file content
    cannot be sent through this tool. Fails if the incident is already closed.

    Returns
    -------
    str
        JSON with ``success`` and confirmation message.
    """
    handler = tool_handler.get_shared_handler()
    data = AddIncidentAttachmentInput(
        incident_number=incident_number,
        file_path=file_path,
        **work_log_options(note_text, work_log_type, view_access, secure_work_log),
    )
    result = await IncidentOperations(handler).add_attachment(data)
    return result.model_dump_json()


@tool(
    description=(
        "Close an Incident, taking ownership and moving it to Resolved. Only works on "
        "an incident created by this agent's own BMC user, from any open status. "
        "Irreversible — there is no tool to reopen it afterwards."
    )
)
async def bmc_close_incident(
    incident_number: Annotated[str, Field(min_length=1, description="Incident Number to close.")],
    description: Annotated[
        str,
        Field(
            min_length=1,
            max_length=INCIDENT_DESCRIPTION_MAX_LENGTH,
            description=(
                "Short closing summary (hard limit: 100 characters — BMC rejects the "
                "whole request above that). Summarize, do not narrate the full "
                "resolution here; put the full explanation in `resolution` or as a "
                "separate note via `bmc_add_incident_note` before closing."
            ),
        ),
    ],
    resolution: Annotated[
        str,
        Field(
            min_length=1,
            description="How the incident was actually solved; replace the placeholder default.",
        ),
    ] = "Solución no especificada",
) -> str:
    """Close an Incident, taking ownership of it and moving it to Resolved.

    Works from any open status, but only on an incident created by this agent's own
    BMC user. There is no tool to reopen it afterwards.

    Returns
    -------
    str
        JSON with ``success`` flag and result message.
    """
    handler = tool_handler.get_shared_handler()
    data = CloseIncidentInput(
        incident_number=incident_number,
        description=description,
        resolution=resolution,
    )
    result = await IncidentOperations(handler).close(data)
    return result.model_dump_json()
