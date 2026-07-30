"""BMC LangChain internal tools for agent-bmc.

Wraps the BMC Helix operations (incidents and work orders) as LangChain @tool
functions using the ``bmc`` package.  All tools share a lazy-initialized
``BaseToolHandler`` so settings are validated only once, at first access.
"""

from __future__ import annotations

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
    DEFAULT_FIRST_NAME,
    DEFAULT_INCIDENT_ASSIGNED_GROUP,
    DEFAULT_LAST_NAME,
    DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
)
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    AR_FIELD_WORK_ORDER_ID,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    INCIDENT_STATUSES,
    WORK_ORDER_STATUSES,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.incident_operations import IncidentOperations
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
    UpdateWorkOrderStatusInput,
    WorkOrderIdInput,
)
from bmc.type_defs.outputs import (
    BaseOutput,
    IncidentDetailData,
    WorkOrderCreatedData,
    WorkOrderDetailData,
)

logger = logging.getLogger(__name__)

_handler: BaseToolHandler | None = None


def _get_handler() -> BaseToolHandler:
    """Return the module-level handler, initializing it on first access.

    Returns
    -------
    BaseToolHandler
        Singleton handler backed by ``BmcSettings`` from environment.
    """
    global _handler  # noqa: PLW0603
    if _handler is None:
        _handler = BaseToolHandler()
    return _handler


def _wo_detail_from_search(
    work_order_id: str,
    values_data: dict[str, ArScalarValue],
) -> WorkOrderDetailData:
    """Build a ``WorkOrderDetailData`` from a raw AR values dict."""
    status = values_data.get("Status", "")
    summary = values_data.get("Summary", "")
    request_id = values_data.get(AR_FIELD_REQUEST_ID, "")
    return WorkOrderDetailData(
        work_order_id=work_order_id,
        request_id=str(request_id) if request_id is not None else "",
        status=str(status) if status is not None else "",
        summary=str(summary) if summary is not None else "",
        values=dict(values_data),
    )


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
        is_healthy = await h.client.health_ping()
    except MCPClientError as exc:
        logger.warning("bmc_health_check failed: %s", exc.message)
        return BaseToolHandler.failure(exc).model_dump_json()
    if is_healthy:
        logger.info("bmc_health_check successful")
        return BaseOutput(success=True, message="BMC session is healthy.").model_dump_json()
    return BaseOutput(
        success=False, message="Error: BMC health check returned unexpected state."
    ).model_dump_json()


# ---------------------------------------------------------------------------
# Work Orders
# ---------------------------------------------------------------------------


@tool
async def bmc_create_work_order(
    summary: str,
    detailed_description: str,
    categorization_tier_1: str,
    categorization_tier_2: str,
    product_cat_tier_1: str,
    product_cat_tier_2: str,
    product_cat_tier_3: str,
    status: Annotated[
        Literal[WORK_ORDER_STATUSES],
        Field(description="Work order status label."),
    ] = DEFAULT_WORK_ORDER_STATUS,
    priority: str = "Medium",
    assigned_group: str = DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
) -> str:
    """Create a Work Order in BMC Helix ARUS (WOI:WorkOrderInterface_Create).

    Take the category tiers, priority and ``assigned_group`` from a single row of the
    ``categorias-requerimientos`` skill: creation will still succeed for combinations
    outside that catalog (there is no backend validation), but the ticket may end up
    inconsistently categorized. Company, submitter and customer identity are fixed per
    environment configuration and must not be provided by the caller.

    Parameters
    ----------
    summary : str
        Short summary of the work order.
    detailed_description : str
        Detailed description text.
    categorization_tier_1 : str
        Operational categorization tier 1, from the ``categorias-requerimientos`` skill.
    categorization_tier_2 : str
        Operational categorization tier 2, same catalog row.
    product_cat_tier_1 : str
        Product categorization tier 1, same catalog row.
    product_cat_tier_2 : str
        Product categorization tier 2, same catalog row.
    product_cat_tier_3 : str
        Product categorization tier 3, same catalog row.
    status : str, optional
        Work order status label, by default ``'Assigned'``.
    priority : str, optional
        Priority, taken from the same catalog row, by default ``'Medium'``.
    assigned_group : str, optional
        Support group, taken from the same catalog row; keep the default only when
        the catalog row does not specify one.

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
        categorization_tier_1=categorization_tier_1,
        categorization_tier_2=categorization_tier_2,
        product_cat_tier_1=product_cat_tier_1,
        product_cat_tier_2=product_cat_tier_2,
        product_cat_tier_3=product_cat_tier_3,
        status=status,
        priority=priority,
        assigned_group=assigned_group,
    )
    values = CreateWorkOrderValues(
        company=DEFAULT_COMPANY,
        first_name=DEFAULT_FIRST_NAME,
        last_name=DEFAULT_LAST_NAME,
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
        assigned_group=data.assigned_group,
    )
    body = EntryValuesMapper.wrap_entry_body(values)
    try:
        created = await h.client.create_work_order_entry(body)
    except MCPClientError as exc:
        logger.info("bmc_create_work_order failed")
        return BaseToolHandler.failure(exc).model_dump_json()
    wo_id = created.values.get_str(AR_FIELD_WORK_ORDER_ID_RESPONSE)
    if not wo_id:
        wo_id = created.values.get_str(AR_FIELD_WORK_ORDER_ID)
    out = WorkOrderCreatedData(
        work_order_id=wo_id,
        request_id=created.values.get_str(AR_FIELD_REQUEST_ID),
    )
    logger.info("bmc_create_work_order ok work_order_id=%s", out.work_order_id)
    return BaseToolHandler.success_toon(out).model_dump_json()


@tool
async def bmc_get_work_order(work_order_id: str) -> str:
    """Read one Work Order by its ID: current status, summary and remaining fields.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write.

    Parameters
    ----------
    work_order_id : str
        Work Order ID (e.g. ``WO0000000000228``).

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
async def bmc_add_work_order_note(
    work_order_id: str,
    note_text: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a note to the activity log of a Work Order, visible to whoever reviews it.

    Fails if the Work Order is already closed.

    Parameters
    ----------
    work_order_id : str
        Target Work Order ID.
    note_text : str
        Text of the note, written as it should be read by whoever reviews the ticket.
    work_log_type : str, optional
        Category of the note in the ticket activity log; keep the default unless
        asked otherwise.
    view_access : str, optional
        Visibility of the note in BMC; keep the default unless asked otherwise.
    secure_work_log : str, optional
        Whether the note is flagged as secure in BMC; keep the default unless
        asked otherwise.

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
    work_order_id: str,
    note_text: str,
    file_path: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a note with one file attached to the activity log of a Work Order.

    The file must already exist on the machine running this agent; file content
    cannot be sent through this tool. Fails if the Work Order is already closed.

    Parameters
    ----------
    work_order_id : str
        Target Work Order ID.
    note_text : str
        Work log detailed description text.
    file_path : str
        Path of the file to attach, as seen by the machine running this agent.
    work_log_type : str, optional
        Work log type, by default ``'General Information'``.
    view_access : str, optional
        View access, by default ``'Public'``.
    secure_work_log : str, optional
        Secure work log flag, by default ``'No'``.

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
    work_order_id: str,
    description: str,
    status: Annotated[
        Literal[WORK_ORDER_STATUSES],
        Field(description="Target status."),
    ] = DEFAULT_WORK_ORDER_UPDATE_STATUS,
) -> str:
    """Move a Work Order to another open status, recording a description of the change.

    To close one use ``bmc_close_work_order`` instead: closing needs a sequence of
    updates that this tool does not perform. Fails if the Work Order is already closed.

    Parameters
    ----------
    work_order_id : str
        Work Order ID used to resolve Request ID via search.
    description : str
        What changed and why; BMC also uses this text as the ticket title.
    status : str, optional
        Target status, by default ``'In Progress'``.

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
    work_order_id: str,
    intermediate_description: str = "Rest API: Resolve WO using RestAPI",
    final_description: str = "Rest API: Resolve Work order via Mosaico",
) -> str:
    """Close a Work Order, taking ownership of it and moving it through Completed to Closed.

    Works from any open status, but only on a Work Order created by this agent's own
    BMC user. Once closed it accepts no further notes, attachments or status changes,
    and there is no tool to reopen it.

    Parameters
    ----------
    work_order_id : str
        Work Order ID to close.
    intermediate_description : str, optional
        Summary of the work actually performed, recorded when moving to Completed.
    final_description : str, optional
        Documentation of the final solution, recorded when moving to Closed.

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
    description: str,
    detailed_decription: str,
    product_categorization_tier_1: str,
    product_categorization_tier_2: str,
    product_categorization_tier_3: str,
    categorization_tier_1: str = "",
    categorization_tier_2: str = "",
    assigned_group: str = DEFAULT_INCIDENT_ASSIGNED_GROUP,
    status: Annotated[
        Literal[INCIDENT_STATUSES],
        Field(description="Incident status."),
    ] = "Assigned",
    reported_source: str = "Direct Input",
    service_type: str = "User Service Restoration",
) -> str:
    """Create an Incident in BMC Helix ARUS (HPD:IncidentInterface_Create).

    Take the category tiers and ``assigned_group`` from a single row of the
    ``categorias-incidentes`` skill. Company, submitter, Impact and Urgency are fixed
    per environment configuration and must not be provided by the caller: every
    incident created here keeps a fixed Impact/Urgency (Critical/Extensive), matching
    the current bmc-mcp behavior.

    Parameters
    ----------
    description : str
        Short incident description.
    detailed_decription : str
        Detailed description (preserves AR field spelling).
    product_categorization_tier_1 : str
        Product categorization tier 1, from the ``categorias-incidentes`` skill.
    product_categorization_tier_2 : str
        Product categorization tier 2, same catalog row.
    product_categorization_tier_3 : str
        Product categorization tier 3, same catalog row.
    categorization_tier_1 : str, optional
        Operational categorization tier 1, same catalog row, by default ``''``.
    categorization_tier_2 : str, optional
        Operational categorization tier 2, same catalog row, by default ``''``.
    assigned_group : str, optional
        Assigned group, taken from the same catalog row; keep the default only when
        the catalog row does not specify one.
    status : str, optional
        Incident status, by default ``'Assigned'``.
    reported_source : str, optional
        Reported source, by default ``'Direct Input'``.
    service_type : str, optional
        Service type, by default ``'User Service Restoration'``.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (TOON-encoded ids on success).
    """
    h = _get_handler()
    data = CreateIncidentInput(
        description=description,
        detailed_decription=detailed_decription,
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
async def bmc_get_incident(incident_number: str) -> str:
    """Read one Incident by its number: current status, description and remaining fields.

    Use it to check a ticket before writing to it, or to confirm the result of a
    previous write.

    Parameters
    ----------
    incident_number : str
        Incident Number (e.g. ``INC000000002106``).

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
async def bmc_add_incident_note(
    incident_number: str,
    note_text: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a note to the activity log of an Incident, visible to whoever reviews it.

    Fails if the incident is already closed.

    Parameters
    ----------
    incident_number : str
        Target Incident Number.
    note_text : str
        Text of the note, written as it should be read by whoever reviews the ticket.
    work_log_type : str, optional
        Category of the note in the ticket activity log; keep the default unless
        asked otherwise.
    view_access : str, optional
        Visibility of the note in BMC; keep the default unless asked otherwise.
    secure_work_log : str, optional
        Whether the note is flagged as secure in BMC; keep the default unless
        asked otherwise.

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
    incident_number: str,
    note_text: str,
    file_path: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a note with one file attached to the activity log of an Incident.

    The file must already exist on the machine running this agent; file content
    cannot be sent through this tool. Fails if the incident is already closed.

    Parameters
    ----------
    incident_number : str
        Target Incident Number.
    note_text : str
        Work log detailed description text.
    file_path : str
        Path of the file to attach, as seen by the machine running this agent.
    work_log_type : str, optional
        Work log type, by default ``'General Information'``.
    view_access : str, optional
        View access, by default ``'Public'``.
    secure_work_log : str, optional
        Secure work log flag, by default ``'No'``.

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
    incident_number: str,
    description: str,
    resolution: str = "Solución no especificada",
) -> str:
    """Close an Incident, taking ownership of it and moving it to Resolved.

    Works from any open status, but only on an incident created by this agent's own
    BMC user. There is no tool to reopen it afterwards.

    Parameters
    ----------
    incident_number : str
        Incident Number to close.
    description : str
        Short summary of the closure, recorded on the incident.
    resolution : str, optional
        How the incident was actually solved; replace the placeholder default.

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
    bmc_add_work_order_note,
    bmc_add_work_order_attachment,
    bmc_update_work_order_status,
    bmc_close_work_order,
    bmc_create_incident,
    bmc_get_incident,
    bmc_add_incident_note,
    bmc_add_incident_attachment,
    bmc_close_incident,
]


def get_bmc_tools() -> list[BaseTool]:
    """Return BMC tools when ``BMC_BASE_URL`` is configured; otherwise empty list.

    Returns
    -------
    list[BaseTool]
        All 12 BMC LangChain tools, or ``[]`` when BMC is not configured.
    """
    if not os.environ.get("BMC_BASE_URL"):
        logger.info("BMC_BASE_URL not set — BMC tools disabled")
        return []
    _get_handler()  # eager initialization to fail fast on bad config
    logger.info("BMC tools loaded: %d", len(_ALL_BMC_TOOLS))
    return list(_ALL_BMC_TOOLS)
