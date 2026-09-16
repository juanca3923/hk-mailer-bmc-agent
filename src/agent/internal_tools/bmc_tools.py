"""BMC LangChain internal tools for agent-bmc.

Wraps the BMC Helix operations (incidents and work orders) as LangChain @tool
functions using the ``bmc`` package.  All tools share a lazy-initialized
``BaseToolHandler`` so settings are validated only once, at first access.
"""

# pylint: disable=too-many-arguments,too-many-positional-arguments
#
# Some ``@tool``-decorated functions below (``bmc_create_work_order``,
# ``bmc_create_incident``) exceed the configured argument limits. This is not
# fixable by restructuring the function, and disabling it here is intentional
# rather than a workaround:
#
# LangChain's ``@tool`` decorator builds the JSON schema the LLM sees directly from
# the function's *own* signature — one schema property per parameter, each with its
# own type/default so the model can fill it independently. That flat parameter list
# is the real, user-facing interface of the tool; it is not incidental complexity.
#
# Packing the parameters into a single ``dataclass``/Pydantic argument does not
# reduce that complexity, it only hides it from Pylint's counter — and it does not
# even work transparently: verified empirically that a function declared as
# ``async def tool_fn(data: SomeModel)`` with ``args_schema=SomeModel`` still gets
# called by LangChain with the model's fields as separate keyword arguments (never
# a single packed object), raising ``TypeError: unexpected keyword argument``. The
# only way to make a single-parameter signature actually work is ``**kwargs: Any``
# reconstructing the model inside the function body — which trades a self-documented,
# type-checked parameter list for an opaque one just to satisfy the linter, with no
# behavior or schema benefit. The BMC creation forms genuinely require this many
# independent fields (categorization tiers, product categories, etc.); the count
# reflects that domain requirement, not a design smell.
from __future__ import annotations

import functools
import logging
import os
from typing import Annotated, Literal

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.business_defaults import (
    DEFAULT_COMPANY,
    DEFAULT_CUSTOMER_COMPANY,
    DEFAULT_CUSTOMER_FIRST_NAME,
    DEFAULT_CUSTOMER_LAST_NAME,
    DEFAULT_INCIDENT_ASSIGNED_GROUP,
    DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
    DEFAULT_WORK_ORDER_SUPPORT_COMPANY,
    DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION,
)
from bmc.libs.constants import (
    AR_FIELD_INCIDENT_NUMBER,
    AR_FIELD_REQUEST_ID,
    AR_FIELD_WORK_ORDER_ID,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    DEFAULT_WORK_LOG_TYPE,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    INCIDENT_DESCRIPTION_MAX_LENGTH,
    INCIDENT_STATUSES,
    MAX_TICKETS_BY_EMAIL_RESULTS,
    WORK_ORDER_STATUSES,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.incident_operations import IncidentOperations
from bmc.libs.helpers.person_lookup import resolve_reporter_identity
from bmc.libs.helpers.work_order_operations import WorkOrderOperations
from bmc.libs.tool_handler import BaseToolHandler
from bmc.type_defs.ar_api import ArScalarValue
from bmc.type_defs.ar_values import CreateWorkOrderValues
from bmc.type_defs.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
    CloseIncidentInput,
    CloseWorkOrderInput,
    CreateIncidentInput,
    CreateWorkOrderInput,
    IncidentNumberInput,
    TicketsByEmailInput,
    UpdateWorkOrderStatusInput,
    WorkOrderIdInput,
)
from bmc.type_defs.outputs import (
    BaseOutput,
    IncidentByEmailRow,
    IncidentDetailData,
    IncidentsByEmailData,
    WorkOrderByEmailRow,
    WorkOrderCreatedData,
    WorkOrderDetailData,
    WorkOrdersByEmailData,
)

logger = logging.getLogger(__name__)


@functools.cache
def _get_handler() -> BaseToolHandler:
    """Return the module-level handler, initializing it on first access.

    Idempotency is provided by ``functools.cache`` (a niladic function, so it runs its
    body only on the first call and returns the cached instance on every call after),
    instead of a module-level flag.

    Returns
    -------
    BaseToolHandler
        Singleton handler backed by ``BmcSettings`` from environment.
    """
    return BaseToolHandler()


def _wo_detail_from_search(
    work_order_id: str,
    values_data: dict[str, ArScalarValue],
) -> WorkOrderDetailData:
    """Build a ``WorkOrderDetailData`` from a raw AR values dict."""
    status = values_data.get("Status", "")
    # AR field is "Description" (same one bmc_create_work_order's summary maps to);
    # "Summary" doesn't hold the subject on this form ("z1D_Summary" exists but is unused).
    summary = values_data.get("Description", "")
    request_id = values_data.get(AR_FIELD_REQUEST_ID, "")
    return WorkOrderDetailData(
        work_order_id=work_order_id,
        request_id=str(request_id) if request_id is not None else "",
        status=str(status) if status is not None else "",
        summary=str(summary) if summary is not None else "",
        values=dict(values_data),
    )


async def _create_work_order_entry(h: BaseToolHandler, values: CreateWorkOrderValues) -> BaseOutput:
    """Create the Work Order entry in BMC and build the resulting tool output.

    Parameters
    ----------
    h : BaseToolHandler
        Initialized BMC tool handler.
    values : CreateWorkOrderValues
        Mapped AR field values for ``WOI:WorkOrderInterface_Create``.

    Returns
    -------
    BaseOutput
        Success with TOON-encoded created ids, or failure output on error.
    """
    try:
        created = await h.client.create_work_order_entry(EntryValuesMapper.wrap_entry_body(values))
    except MCPClientError as exc:
        logger.info("bmc_create_work_order failed")
        return BaseToolHandler.failure(exc)
    wo_id = created.values.get_str(AR_FIELD_WORK_ORDER_ID_RESPONSE) or created.values.get_str(AR_FIELD_WORK_ORDER_ID)
    out = WorkOrderCreatedData(
        work_order_id=wo_id,
        request_id=created.values.get_str(AR_FIELD_REQUEST_ID),
    )
    logger.info("bmc_create_work_order ok work_order_id=%s", out.work_order_id)
    return BaseToolHandler.success_toon(out)


def _incident_detail_from_search(
    incident_number: str,
    values_data: dict[str, ArScalarValue],
) -> IncidentDetailData:
    """Build an ``IncidentDetailData`` from a raw AR values dict."""
    status = values_data.get("Status", "")
    description = values_data.get("Description", "")
    request_id = values_data.get(AR_FIELD_REQUEST_ID, "")
    return IncidentDetailData(
        incident_number=incident_number,
        request_id=str(request_id) if request_id is not None else "",
        status=str(status) if status is not None else "",
        description=str(description) if description is not None else "",
        values=dict(values_data),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@tool
async def bmc_health_check() -> str:
    """Verify BMC JWT session and API reachability with a lightweight authenticated GET.

    Does not create or modify tickets.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` fields.
    """
    h = _get_handler()
    try:
        await h.client.health_ping()
    except MCPClientError as exc:
        logger.warning("bmc_health_check failed: %s", exc.message)
        return BaseToolHandler.failure(exc).model_dump_json()
    logger.info("bmc_health_check successful")
    return BaseOutput(success=True, message="BMC session is healthy.").model_dump_json()


# ---------------------------------------------------------------------------
# Work Orders
# ---------------------------------------------------------------------------


@tool
async def bmc_create_work_order(
    summary: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Short, specific subject line: what is requested and for whom or which "
                'system (e.g. "New network user - Juan Perez, Bogota site"), never a '
                'generic label like "User request".'
            ),
        ),
    ],
    detailed_description: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Full request detail: who needs it, exactly what must be done, and any "
                "data required to execute it (access, equipment, location, dates) — "
                "enough for the service desk to act without asking the user again."
            ),
        ),
    ],
    reporter_email: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Email of the person requesting this Work Order. Required: looked up in "
                "CTM:People to fill the submitter's First/Last Name with the real requester "
                "(never the fixed Customer identity). Never invent or guess this value — ask "
                "the user for it, or take it from the incoming structured message in A2A mode."
            ),
        ),
    ],
    categorization_tier_1: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Operational categorization tier 1: from the matching categorias-<dominio> "
                "skill row when one applies, otherwise the catch-all value from "
                "guia-creacion-tickets (section 1)."
            ),
        ),
    ],
    categorization_tier_2: Annotated[
        str,
        Field(min_length=1, description="Operational categorization tier 2, same row/catch-all as tier 1."),
    ],
    product_cat_tier_1: Annotated[
        str,
        Field(min_length=1, description="Product categorization tier 1, same row/catch-all as tier 1."),
    ],
    product_cat_tier_2: Annotated[
        str,
        Field(min_length=1, description="Product categorization tier 2, same row/catch-all as tier 1."),
    ],
    product_cat_tier_3: Annotated[
        str,
        Field(min_length=1, description="Product categorization tier 3, same row/catch-all as tier 1."),
    ],
    status: Annotated[
        Literal[WORK_ORDER_STATUSES],
        Field(description="Work order status label."),
    ] = DEFAULT_WORK_ORDER_STATUS,
    priority: Annotated[
        str,
        Field(description="Priority, taken from the same catalog row as the categorization tiers."),
    ] = "Medium",
    assigned_group: Annotated[
        str,
        Field(
            description=(
                "Support group, taken from the same catalog row; keep the default only when "
                "no domain skill applies."
            ),
        ),
    ] = DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
) -> str:
    """Create a Work Order in BMC Helix ARUS (WOI:WorkOrderInterface_Create).

    Take the category tiers and priority from a single row of a matching
    ``categorias-<dominio>`` skill (e.g. ``categorias-eventos``,
    ``categorias-usuario``) when one applies to this request: creation will still
    succeed for combinations outside that catalog (there is no backend validation),
    but the ticket may end up inconsistently categorized. When NO domain skill
    applies, use the fixed catch-all combination documented in
    ``guia-creacion-tickets`` (section 1) instead — read that skill for the exact
    values, never guess a different combination or leave these blank. Company,
    customer identity and the Support Company/Organization (BMC only honors the
    caller's ``Support Group Name`` when these two travel together in the same
    payload) are fixed per environment configuration and must not be provided by the
    caller. The submitter's First/Last Name are resolved from ``reporter_email``
    against BMC's ``CTM:People`` — this call fails with no Work Order created if
    that person cannot be found.

    Parameters
    ----------
    See each parameter's own description in the tool schema for format, examples
    and defaults.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded ids on success).
    """
    h = _get_handler()
    blocked = h.ensure_write_allowed()
    if blocked is not None:
        return blocked.model_dump_json()
    data = CreateWorkOrderInput(
        summary=summary,
        detailed_description=detailed_description,
        reporter_email=reporter_email,
        categorization_tier_1=categorization_tier_1,
        categorization_tier_2=categorization_tier_2,
        product_cat_tier_1=product_cat_tier_1,
        product_cat_tier_2=product_cat_tier_2,
        product_cat_tier_3=product_cat_tier_3,
        status=status,
        priority=priority,
        assigned_group=assigned_group,
    )
    identity = await resolve_reporter_identity(h.client, data.reporter_email)
    if isinstance(identity, BaseOutput):
        return identity.model_dump_json()
    values = CreateWorkOrderValues(
        company=DEFAULT_COMPANY,
        first_name=identity.first_name,
        last_name=identity.last_name,
        summary=data.summary,
        detailed_description=data.detailed_description,
        status=data.status,
        customer_first_name=DEFAULT_CUSTOMER_FIRST_NAME,
        customer_last_name=DEFAULT_CUSTOMER_LAST_NAME,
        customer_company=DEFAULT_CUSTOMER_COMPANY,
        categorization_tier_1=data.categorization_tier_1,
        categorization_tier_2=data.categorization_tier_2,
        product_cat_tier_1=data.product_cat_tier_1,
        product_cat_tier_2=data.product_cat_tier_2,
        product_cat_tier_3=data.product_cat_tier_3,
        priority=data.priority,
        support_company=DEFAULT_WORK_ORDER_SUPPORT_COMPANY,
        support_organization=DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION,
        assigned_group=data.assigned_group,
    )
    output = await _create_work_order_entry(h, values)
    return output.model_dump_json()


@tool
async def bmc_get_work_order(
    work_order_id: Annotated[
        str,
        Field(min_length=1, description="Work Order ID to look up (e.g. WO0000000000228)."),
    ],
) -> str:
    """Read one Work Order by its ID: current status, summary and remaining fields.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded detail on success).
    """
    h = _get_handler()
    data = WorkOrderIdInput(work_order_id=work_order_id)
    try:
        result = await h.client.search_work_order(data.work_order_id)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    first = result.first_values()
    if first is None:
        return BaseOutput(
            success=False,
            message=f"Error: No se encontró la orden de trabajo {data.work_order_id}.",
        ).model_dump_json()
    detail = _wo_detail_from_search(data.work_order_id, first.data)
    return BaseToolHandler.success_toon(detail).model_dump_json()


@tool
async def bmc_list_work_orders_by_email(
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
    """List work orders requested by one person, searched by their email.

    Matches on the same ``reporter_email`` value passed at creation time — never the
    BMC-resolved login id. Returns a short summary per row (id, status, summary), not
    the full detail ``bmc_get_work_order`` returns for one ticket; call that tool with
    a specific id from these results if you need the full detail.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded rows on success).
    """
    h = _get_handler()
    data = TicketsByEmailInput(email=email, limit=limit)
    try:
        result = await h.client.search_work_orders_by_email(data.email)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    total = len(result.entries)
    rows = [
        WorkOrderByEmailRow(
            work_order_id=str(e.values.data.get(AR_FIELD_WORK_ORDER_ID, "")),
            status=str(e.values.data.get("Status", "")),
            summary=str(e.values.data.get("Description", "")),
        )
        for e in result.entries[: data.limit]
    ]
    out = WorkOrdersByEmailData(
        email=data.email,
        total_found=total,
        returned=len(rows),
        truncated=total > len(rows),
        work_orders=rows,
    )
    logger.info("bmc_list_work_orders_by_email ok email=%s total_found=%d", data.email, total)
    return BaseToolHandler.success_toon(out).model_dump_json()


@tool
async def bmc_add_work_order_note(
    work_order_id: Annotated[str, Field(min_length=1, description="Target Work Order ID.")],
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
    """Add a note to the activity log of a Work Order, visible to whoever reviews it.

    Fails if the Work Order is already closed.

    Returns
    -------
    str
        JSON with ``success`` and confirmation message.
    """
    data = AddWorkOrderNoteInput(
        work_order_id=work_order_id,
        note_text=note_text,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    result = await WorkOrderOperations(_get_handler()).add_note(data)
    return result.model_dump_json()


@tool
async def bmc_add_work_order_attachment(
    work_order_id: Annotated[str, Field(min_length=1, description="Target Work Order ID.")],
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
    """Add a note with one file attached to the activity log of a Work Order.

    The file must already exist on the machine running this agent; file content
    cannot be sent through this tool. Fails if the Work Order is already closed.

    Returns
    -------
    str
        JSON with ``success`` and confirmation message.
    """
    h = _get_handler()
    data = AddWorkOrderAttachmentInput(
        work_order_id=work_order_id,
        note_text=note_text,
        file_path=file_path,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    result = await WorkOrderOperations(h).add_attachment(data)
    return result.model_dump_json()


@tool
async def bmc_update_work_order_status(
    work_order_id: Annotated[
        str,
        Field(min_length=1, description="Work Order ID used to resolve Request ID via search."),
    ],
    description: Annotated[
        str,
        Field(min_length=1, description="What changed and why; BMC also uses this text as the ticket title."),
    ],
    status: Annotated[
        Literal[WORK_ORDER_STATUSES],
        Field(description="Target status."),
    ] = DEFAULT_WORK_ORDER_UPDATE_STATUS,
) -> str:
    """Move a Work Order to another open status, recording a description of the change.

    To close one use ``bmc_close_work_order`` instead: closing needs a sequence of
    updates that this tool does not perform. Fails if the Work Order is already closed.

    Returns
    -------
    str
        JSON with ``success`` and confirmation message.
    """
    h = _get_handler()
    data = UpdateWorkOrderStatusInput(
        work_order_id=work_order_id,
        description=description,
        status=status,
    )
    result = await WorkOrderOperations(h).update_status(data)
    return result.model_dump_json()


@tool
async def bmc_close_work_order(
    work_order_id: Annotated[str, Field(min_length=1, description="Work Order ID to close.")],
    intermediate_description: Annotated[
        str,
        Field(
            min_length=1,
            description="Summary of the work actually performed, recorded when moving to Completed.",
        ),
    ] = "Rest API: Resolve WO using RestAPI",
    final_description: Annotated[
        str,
        Field(min_length=1, description="Documentation of the final solution, recorded when moving to Closed."),
    ] = "Rest API: Resolve Work order via Mosaico",
) -> str:
    """Close a Work Order, taking ownership of it and moving it through Completed to Closed.

    Works from any open status, but only on a Work Order created by this agent's own
    BMC user. Once closed it accepts no further notes, attachments or status changes,
    and there is no tool to reopen it.

    Returns
    -------
    str
        JSON with ``success`` flag and result message.
    """
    h = _get_handler()
    data = CloseWorkOrderInput(
        work_order_id=work_order_id,
        intermediate_description=intermediate_description,
        final_description=final_description,
    )
    result = await WorkOrderOperations(h).close(data)
    return result.model_dump_json()


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


@tool
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
                "Email of the person reporting this incident. Required: looked up in "
                "CTM:People to fill the submitter's First/Last Name with the real reporter. "
                "Never invent or guess this value — ask the user for it, or take it from the "
                "incoming structured message in A2A mode."
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
        Literal[INCIDENT_STATUSES],
        Field(description="Incident status."),
    ] = "Assigned",
    reported_source: Annotated[str, Field(description="Reported source.")] = "Direct Input",
    service_type: Annotated[str, Field(description="Service type.")] = "User Service Restoration",
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
    See each parameter's own description in the tool schema for format, examples
    and defaults.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded ids on success).
    """
    h = _get_handler()
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
    result = await IncidentOperations(h).create(data)
    return result.model_dump_json()


@tool
async def bmc_get_incident(
    incident_number: Annotated[
        str,
        Field(min_length=1, description="Incident Number to look up (e.g. INC000000002106)."),
    ],
) -> str:
    """Read one Incident by its number: current status, description and remaining fields.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded detail on success).
    """
    h = _get_handler()
    data = IncidentNumberInput(incident_number=incident_number)
    try:
        result = await h.client.search_incident(data.incident_number)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    first = result.first_values()
    if first is None:
        return BaseOutput(
            success=False,
            message=f"Error: No se encontró el incidente {data.incident_number}.",
        ).model_dump_json()
    detail = _incident_detail_from_search(data.incident_number, first.data)
    return BaseToolHandler.success_toon(detail).model_dump_json()


@tool
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
    BMC-resolved login id. Returns a short summary per row (number, status,
    description), not the full detail ``bmc_get_incident`` returns for one ticket;
    call that tool with a specific number from these results if you need the full
    detail.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded rows on success).
    """
    h = _get_handler()
    data = TicketsByEmailInput(email=email, limit=limit)
    try:
        result = await h.client.search_incidents_by_email(data.email)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    total = len(result.entries)
    rows = [
        IncidentByEmailRow(
            incident_number=str(e.values.data.get(AR_FIELD_INCIDENT_NUMBER, "")),
            status=str(e.values.data.get("Status", "")),
            description=str(e.values.data.get("Description", "")),
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


@tool
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
        note_text=note_text,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    result = await IncidentOperations(_get_handler()).add_note(data)
    return result.model_dump_json()


@tool
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
    h = _get_handler()
    data = AddIncidentAttachmentInput(
        incident_number=incident_number,
        note_text=note_text,
        file_path=file_path,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    result = await IncidentOperations(h).add_attachment(data)
    return result.model_dump_json()


@tool
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
    h = _get_handler()
    data = CloseIncidentInput(
        incident_number=incident_number,
        description=description,
        resolution=resolution,
    )
    result = await IncidentOperations(h).close(data)
    return result.model_dump_json()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ALL_BMC_TOOLS: list[BaseTool] = [
    bmc_health_check,
    bmc_create_work_order,
    bmc_get_work_order,
    bmc_list_work_orders_by_email,
    bmc_add_work_order_note,
    bmc_add_work_order_attachment,
    bmc_update_work_order_status,
    bmc_close_work_order,
    bmc_create_incident,
    bmc_get_incident,
    bmc_list_incidents_by_email,
    bmc_add_incident_note,
    bmc_add_incident_attachment,
    bmc_close_incident,
]


def get_bmc_tools() -> list[BaseTool]:
    """Return BMC tools when ``BMC_BASE_URL`` is configured; otherwise empty list.

    Returns
    -------
    list[BaseTool]
        All 14 BMC LangChain tools, or ``[]`` when BMC is not configured.
    """
    if not os.environ.get("BMC_BASE_URL"):
        logger.info("BMC_BASE_URL not set — BMC tools disabled")
        return []
    _get_handler()
    logger.info("BMC tools loaded: %d", len(_ALL_BMC_TOOLS))
    return list(_ALL_BMC_TOOLS)
