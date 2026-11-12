"""Work Order LangChain tools for agent-bmc.

Split out of ``bmc_tools`` (which stays as the thin aggregator + registry) once that
module grew past the repo's 1000-line-per-module limit. Shares the same lazy
``BaseToolHandler`` singleton via ``bmc.libs.tool_handler.get_shared_handler()`` —
deliberately not imported from ``bmc_tools`` itself, to avoid a cyclic import with
the aggregator that registers this module's tools.
"""

# pylint: disable=too-many-arguments,too-many-positional-arguments
#
# ``bmc_create_work_order`` exceeds the configured argument limit. This is not
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
# behavior or schema benefit. The BMC creation form genuinely requires this many
# independent fields (categorization tiers, product categories, etc.); the count
# reflects that domain requirement, not a design smell.
from __future__ import annotations

import logging
from typing import Annotated, Literal

from langchain_core.tools import tool
from pydantic import Field

from bmc.exceptions.mcp import MCPClientError
from bmc.libs import tool_handler
from bmc.libs.business_defaults import (
    DEFAULT_COMPANY,
    DEFAULT_CUSTOMER_COMPANY,
    DEFAULT_CUSTOMER_FIRST_NAME,
    DEFAULT_CUSTOMER_LAST_NAME,
    DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
    DEFAULT_WORK_ORDER_SUPPORT_COMPANY,
    DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION,
)
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    AR_FIELD_WORK_ORDER_ASGRP,
    AR_FIELD_WORK_ORDER_ID,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    DEFAULT_WORK_LOG_TYPE,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    MAX_TICKETS_BY_EMAIL_RESULTS,
    WORK_ORDER_STATUSES,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.person_lookup import resolve_reporter_identity
from bmc.libs.helpers.work_order_operations import WorkOrderOperations
from bmc.libs.tool_handler import BaseToolHandler
from bmc.type_defs.ar_api import ArScalarValue
from bmc.type_defs.ar_values import CreateWorkOrderValues
from bmc.type_defs.inputs import (
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
    CloseWorkOrderInput,
    CreateWorkOrderInput,
    TicketsByEmailInput,
    UpdateWorkOrderStatusInput,
    WorkOrderIdInput,
)
from bmc.type_defs.outputs import (
    BaseOutput,
    WorkOrderByEmailRow,
    WorkOrderCreatedData,
    WorkOrderDetailData,
    WorkOrdersByEmailData,
)

logger = logging.getLogger(__name__)


def _wo_detail_from_search(
    work_order_id: str,
    values_data: dict[str, ArScalarValue],
) -> WorkOrderDetailData:
    """Build a lean ``WorkOrderDetailData`` (title/status/assigned group only) from a raw AR values dict."""
    status = values_data.get("Status", "")
    # AR field is "Description" (same one bmc_create_work_order's summary maps to);
    # "Summary" doesn't hold the subject on this form ("z1D_Summary" exists but is unused).
    summary = values_data.get("Description", "")
    # "ASGRP" reflects the real assigned group; the create-time alias ("Support Group
    # Name") always reads back as the fixed desk default — verified against BMC.
    assigned_group = values_data.get(AR_FIELD_WORK_ORDER_ASGRP, "")
    return WorkOrderDetailData(
        work_order_id=work_order_id,
        status=str(status) if status is not None else "",
        summary=str(summary) if summary is not None else "",
        assigned_group=str(assigned_group) if assigned_group is not None else "",
    )


async def _create_work_order_entry(handler: BaseToolHandler, values: CreateWorkOrderValues) -> BaseOutput:
    """Create the Work Order entry in BMC and build the resulting tool output.

    Parameters
    ----------
    handler : BaseToolHandler
        Initialized BMC tool handler.
    values : CreateWorkOrderValues
        Mapped AR field values for ``WOI:WorkOrderInterface_Create``.

    Returns
    -------
    BaseOutput
        Success with TOON-encoded created ids, or failure output on error.
    """
    try:
        created = await handler.client.create_work_order_entry(EntryValuesMapper.wrap_entry_body(values))
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


@tool(
    description=(
        "Create a Work Order in BMC Helix ARUS. Categorization must come from a single "
        "row of a matching categorias-<domain> skill, or the fixed catch-all from "
        "guia-creacion-tickets when no domain applies — never invented. Company, "
        "customer identity and Support Company/Organization are fixed and must not be "
        "passed. Fails with no Work Order created if reporter_email does not match a "
        "real, already-registered person."
    )
)
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
                "Email of the person this Work Order is filed on behalf of — the real "
                "requester, never the fixed Customer identity. Always required, regardless "
                "of how it was obtained. Must match a real, already-registered person; "
                "never a fabricated or guessed address."
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
        Literal[WORK_ORDER_STATUSES],  # type: ignore[valid-type]  # tuple constant expands to Literal values at runtime
        Field(description="Work order status at creation; keep the default unless told otherwise."),
    ] = DEFAULT_WORK_ORDER_STATUS,
    priority: Annotated[
        str,
        Field(description="Priority, taken from the same catalog row as the categorization tiers."),
    ] = "Medium",
    assigned_group: Annotated[
        str,
        Field(
            description=(
                "Support group, taken from the same catalog row; keep the default only when no domain skill applies."
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
    Each parameter is documented on its own ``Annotated``/``Field`` above — not
    repeated here.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded ids on success).
    """
    handler = tool_handler.get_shared_handler()
    blocked = handler.ensure_write_allowed()
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
    identity = await resolve_reporter_identity(handler.client, data.reporter_email)
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
    output = await _create_work_order_entry(handler, values)
    return output.model_dump_json()


@tool(
    description=(
        "Look up one Work Order by ID: title, status and assigned group only — never "
        "the detailed description or notes, which can carry sensitive data. Use before "
        "writing to a ticket, or to confirm the result of a previous write."
    )
)
async def bmc_get_work_order(
    work_order_id: Annotated[
        str,
        Field(min_length=1, description="Work Order ID to look up (e.g. WO0000000000228)."),
    ],
) -> str:
    """Read one Work Order by its ID: title, current status and assigned group.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write. Intentionally does not return the detailed description, notes or
    any other raw BMC field — those can carry sensitive data.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded detail on success).
    """
    handler = tool_handler.get_shared_handler()
    data = WorkOrderIdInput(work_order_id=work_order_id)
    try:
        result = await handler.client.search_work_order(data.work_order_id)
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


@tool(
    description=(
        "List work orders for one person, searched by the email they used as "
        "reporter_email at creation — not their BMC-resolved login id. One row per "
        "ticket: title, status and assigned group only; capped and flagged if there "
        "are more matches than returned."
    )
)
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
        result = await handler.client.search_work_orders_by_email(data.email)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    total = len(result.entries)
    rows = [
        WorkOrderByEmailRow(
            work_order_id=str(e.values.data.get(AR_FIELD_WORK_ORDER_ID, "")),
            status=str(e.values.data.get("Status", "")),
            summary=str(e.values.data.get("Description", "")),
            assigned_group=str(e.values.data.get(AR_FIELD_WORK_ORDER_ASGRP, "")),
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


@tool(
    description=(
        "Add a note to a Work Order's activity log, visible to whoever reviews the "
        "ticket. Fails if the Work Order is already closed."
    )
)
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
    result = await WorkOrderOperations(tool_handler.get_shared_handler()).add_note(data)
    return result.model_dump_json()


@tool(
    description=(
        "Add a note with one file attached to a Work Order's activity log. The file "
        "must already exist on the machine running this agent — its content cannot be "
        "sent through this tool. Fails if the Work Order is already closed."
    )
)
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
    handler = tool_handler.get_shared_handler()
    data = AddWorkOrderAttachmentInput(
        work_order_id=work_order_id,
        note_text=note_text,
        file_path=file_path,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    result = await WorkOrderOperations(handler).add_attachment(data)
    return result.model_dump_json()


@tool(
    description=(
        "Move a Work Order to another open status, recording why. To close one use "
        "bmc_close_work_order instead — this tool does not perform the closing "
        "sequence. Fails if the Work Order is already closed."
    )
)
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
        Literal[WORK_ORDER_STATUSES],  # type: ignore[valid-type]  # tuple constant expands to Literal values at runtime
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
    handler = tool_handler.get_shared_handler()
    data = UpdateWorkOrderStatusInput(
        work_order_id=work_order_id,
        description=description,
        status=status,
    )
    result = await WorkOrderOperations(handler).update_status(data)
    return result.model_dump_json()


@tool(
    description=(
        "Close a Work Order, taking ownership and moving it through Completed to "
        "Closed. Only works on a Work Order created by this agent's own BMC user, "
        "from any open status. Irreversible — once closed it accepts no further "
        "notes, attachments or status changes, and there is no tool to reopen it."
    )
)
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
    handler = tool_handler.get_shared_handler()
    data = CloseWorkOrderInput(
        work_order_id=work_order_id,
        intermediate_description=intermediate_description,
        final_description=final_description,
    )
    result = await WorkOrderOperations(handler).close(data)
    return result.model_dump_json()
