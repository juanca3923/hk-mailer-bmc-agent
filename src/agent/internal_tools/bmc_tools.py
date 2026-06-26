"""BMC LangChain internal tools for agent-bmc.

Wraps the BMC Helix operations (incidents and work orders) as LangChain @tool
functions using the ``bmc`` package.  All tools share a lazy-initialized
``BaseToolHandler`` so settings are validated only once, at first access.
"""

from __future__ import annotations

import logging
import os

from langchain_core.tools import BaseTool, tool

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.business_defaults import (
    DEFAULT_COMPANY,
    DEFAULT_CUSTOMER_COMPANY,
    DEFAULT_CUSTOMER_FIRST_NAME,
    DEFAULT_CUSTOMER_LAST_NAME,
    DEFAULT_FIRST_NAME,
    DEFAULT_INCIDENT_ASSIGNED_GROUP,
    DEFAULT_LAST_NAME,
)
from bmc.libs.constants import (
    AR_FIELD_INCIDENT_NUMBER,
    AR_FIELD_REQUEST_ID,
    AR_FIELD_WORK_ORDER_ID,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
    DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
    DEFAULT_INCIDENT_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.incident_operations import IncidentOperations
from bmc.libs.helpers.multipart_builder import MultipartBuilder
from bmc.libs.helpers.work_order_operations import WorkOrderOperations
from bmc.libs.tool_handler import BaseToolHandler
from bmc.type_defs.ar_api import ArScalarValue
from bmc.type_defs.ar_values import (
    CreateIncidentValues,
    CreateWorkOrderValues,
    WorkInfoIncidentValues,
    WorkInfoWorkOrderValues,
)
from bmc.type_defs.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    CloseIncidentInput,
    CreateIncidentInput,
    CreateWorkOrderInput,
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
    CloseWorkOrderInput,
    IncidentNumberInput,
    UpdateWorkOrderStatusInput,
    WorkOrderIdInput,
)
from bmc.type_defs.outputs import (
    BaseOutput,
    IncidentCreatedData,
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
async def health_check() -> str:
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
        logger.warning("health_check failed: %s", exc.message)
        return BaseToolHandler.failure(exc).model_dump_json()
    if is_healthy:
        logger.info("health_check successful")
        return BaseOutput(success=True, message="BMC session is healthy.").model_dump_json()
    return BaseOutput(
        success=False, message="Error: BMC health check returned unexpected state."
    ).model_dump_json()


# ---------------------------------------------------------------------------
# Work Orders
# ---------------------------------------------------------------------------


@tool
async def create_work_order(
    summary: str,
    detailed_description: str,
    categorization_tier_1: str,
    categorization_tier_2: str,
    product_cat_tier_1: str,
    product_cat_tier_2: str,
    product_cat_tier_3: str,
    status: str = DEFAULT_WORK_ORDER_STATUS,
    priority: str = "Medium",
) -> str:
    """Create a Work Order in BMC Helix ARUS (WOI:WorkOrderInterface_Create).

    Company, submitter and customer identity are fixed per environment configuration
    and must not be provided by the caller.

    Parameters
    ----------
    summary : str
        Short summary of the work order.
    detailed_description : str
        Detailed description text.
    categorization_tier_1 : str
        Categorization tier 1.
    categorization_tier_2 : str
        Categorization tier 2.
    product_cat_tier_1 : str
        Product categorization tier 1.
    product_cat_tier_2 : str
        Product categorization tier 2.
    product_cat_tier_3 : str
        Product categorization tier 3.
    status : str, optional
        Work order status label, by default ``'Assigned'``.
    priority : str, optional
        Priority, by default ``'Medium'``.

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
    )
    body = EntryValuesMapper.wrap_entry_body(values)
    try:
        created = await h.client.create_work_order_entry(body)
    except MCPClientError as exc:
        logger.info("create_work_order failed")
        return BaseToolHandler.failure(exc).model_dump_json()
    wo_id = created.values.get_str(AR_FIELD_WORK_ORDER_ID_RESPONSE)
    if not wo_id:
        wo_id = created.values.get_str(AR_FIELD_WORK_ORDER_ID)
    out = WorkOrderCreatedData(
        work_order_id=wo_id,
        request_id=created.values.get_str(AR_FIELD_REQUEST_ID),
    )
    logger.info("create_work_order ok work_order_id=%s", out.work_order_id)
    return BaseToolHandler.success_toon(out).model_dump_json()


@tool
async def get_work_order(work_order_id: str) -> str:
    """Search a Work Order by Work Order ID in BMC Helix.

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
async def add_work_order_note(
    work_order_id: str,
    note_text: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a work log note to a Work Order without attachment (WOI:WorkInfo multipart).

    Parameters
    ----------
    work_order_id : str
        Target Work Order ID.
    note_text : str
        Work log detailed description text.
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
    blocked = h.ensure_write_allowed()
    if blocked is not None:
        return blocked.model_dump_json()
    data = AddWorkOrderNoteInput(
        work_order_id=work_order_id,
        note_text=note_text,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    values = WorkInfoWorkOrderValues(
        work_order_id=data.work_order_id,
        work_log_type=data.work_log_type,
        view_access=data.view_access,
        secure_work_log=data.secure_work_log,
        detailed_description=data.note_text,
    )
    work_info_body = MultipartBuilder.build(values)
    try:
        await h.client.post_work_info(work_info_body)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    logger.info("add_work_order_note ok work_order_id=%s", data.work_order_id)
    return BaseOutput(
        success=True, message=f"Nota añadida a {data.work_order_id}."
    ).model_dump_json()


@tool
async def add_work_order_attachment(
    work_order_id: str,
    note_text: str,
    file_path: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a work log entry with file attachment to a Work Order (WOI:WorkInfo multipart).

    ``file_path`` must be readable by the agent process.

    Parameters
    ----------
    work_order_id : str
        Target Work Order ID.
    note_text : str
        Work log detailed description text.
    file_path : str
        Local path readable by the agent process.
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
async def update_work_order_status(
    work_order_id: str,
    description: str,
    status: str = DEFAULT_WORK_ORDER_UPDATE_STATUS,
) -> str:
    """PUT an intermediate status on a Work Order using Request ID from a prior search.

    Parameters
    ----------
    work_order_id : str
        Work Order ID used to resolve Request ID via search.
    description : str
        Description text for the status update.
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
async def close_work_order(
    work_order_id: str,
    description: str,
    intermediate_description: str = "Rest API: Resolve WO using RestAPI",
    final_description: str = "Rest API: Resolve Work order via Mosaico",
    final_status: str = DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
    status_reason: str | None = None,
) -> str:
    """Close a Work Order: search Request ID, PUT Completed+Assignee, then PUT Closed.

    Parameters
    ----------
    work_order_id : str
        Work Order ID to close.
    description : str
        Closure description stored on the input model.
    intermediate_description : str, optional
        Description for the first PUT (Completed + Assignee).
    final_description : str, optional
        Description for the final close PUT.
    final_status : str, optional
        Final ``Status`` on close PUT, by default ``'Closed'``.
    status_reason : str | None, optional
        Status reason when required by BMC characterization.

    Returns
    -------
    str
        JSON with ``success`` flag and result message.
    """
    h = _get_handler()
    data = CloseWorkOrderInput(
        work_order_id=work_order_id,
        description=description,
        intermediate_description=intermediate_description,
        final_description=final_description,
        final_status=final_status,
        status_reason=status_reason,
    )
    result = await WorkOrderOperations(h).close(data)
    return result.model_dump_json()


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


@tool
async def create_incident(
    description: str,
    detailed_decription: str,
    product_categorization_tier_1: str,
    product_categorization_tier_2: str,
    product_categorization_tier_3: str,
    categorization_tier_1: str = "",
    categorization_tier_2: str = "",
    impact: str = "3-Moderate/Limited",
    urgency: str = "3-Medium",
    status: str = DEFAULT_INCIDENT_STATUS,
    reported_source: str = "Direct Input",
    service_type: str = "User Service Restoration",
) -> str:
    """Create an Incident in BMC Helix ARUS (HPD:IncidentInterface_Create).

    Company, submitter and assigned group are fixed per environment configuration
    and must not be provided by the caller.

    Parameters
    ----------
    description : str
        Short incident description.
    detailed_decription : str
        Detailed description (preserves AR field spelling).
    product_categorization_tier_1 : str
        Product categorization tier 1.
    product_categorization_tier_2 : str
        Product categorization tier 2.
    product_categorization_tier_3 : str
        Product categorization tier 3.
    categorization_tier_1 : str, optional
        Categorization tier 1, by default ``''``.
    categorization_tier_2 : str, optional
        Categorization tier 2, by default ``''``.
    impact : str, optional
        Impact value, by default ``'3-Moderate/Limited'``.
    urgency : str, optional
        Urgency value, by default ``'3-Medium'``.
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
    blocked = h.ensure_write_allowed()
    if blocked is not None:
        return blocked.model_dump_json()
    data = CreateIncidentInput(
        description=description,
        detailed_decription=detailed_decription,
        categorization_tier_1=categorization_tier_1,
        categorization_tier_2=categorization_tier_2,
        product_categorization_tier_1=product_categorization_tier_1,
        product_categorization_tier_2=product_categorization_tier_2,
        product_categorization_tier_3=product_categorization_tier_3,
        impact=impact,
        urgency=urgency,
        status=status,
        reported_source=reported_source,
        service_type=service_type,
    )
    values = CreateIncidentValues(
        company=DEFAULT_COMPANY,
        first_name=DEFAULT_FIRST_NAME,
        last_name=DEFAULT_LAST_NAME,
        description=data.description,
        impact=data.impact,
        urgency=data.urgency,
        status=data.status,
        reported_source=data.reported_source,
        service_type=data.service_type,
        detailed_decription=data.detailed_decription,
        categorization_tier_1=data.categorization_tier_1,
        categorization_tier_2=data.categorization_tier_2,
        product_categorization_tier_1=data.product_categorization_tier_1,
        product_categorization_tier_2=data.product_categorization_tier_2,
        product_categorization_tier_3=data.product_categorization_tier_3,
        assigned_group=DEFAULT_INCIDENT_ASSIGNED_GROUP,
    )
    body = EntryValuesMapper.wrap_entry_body(values)
    try:
        created = await h.client.create_incident_entry(body)
    except MCPClientError as exc:
        logger.info("create_incident failed")
        return BaseToolHandler.failure(exc).model_dump_json()
    out = IncidentCreatedData(
        incident_number=created.values.get_str(AR_FIELD_INCIDENT_NUMBER),
        description=created.values.get_str("Description"),
    )
    logger.info("create_incident ok incident_number=%s", out.incident_number)
    return BaseToolHandler.success_toon(out).model_dump_json()


@tool
async def get_incident(incident_number: str) -> str:
    """Search an Incident by Incident Number in BMC Helix.

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
async def add_incident_note(
    incident_number: str,
    note_text: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a work log note to an Incident without attachment (WOI:WorkInfo multipart).

    Parameters
    ----------
    incident_number : str
        Target Incident Number.
    note_text : str
        Work log detailed description text.
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
    blocked = h.ensure_write_allowed()
    if blocked is not None:
        return blocked.model_dump_json()
    data = AddIncidentNoteInput(
        incident_number=incident_number,
        note_text=note_text,
        work_log_type=work_log_type,
        view_access=view_access,
        secure_work_log=secure_work_log,
    )
    values = WorkInfoIncidentValues(
        incident_number=data.incident_number,
        work_log_type=data.work_log_type,
        view_access=data.view_access,
        secure_work_log=data.secure_work_log,
        detailed_description=data.note_text,
    )
    work_info_body = MultipartBuilder.build(values)
    try:
        await h.client.post_work_info(work_info_body)
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    logger.info("add_incident_note ok incident_number=%s", data.incident_number)
    return BaseOutput(
        success=True, message=f"Nota añadida a {data.incident_number}."
    ).model_dump_json()


@tool
async def add_incident_attachment(
    incident_number: str,
    note_text: str,
    file_path: str,
    work_log_type: str = "General Information",
    view_access: str = "Public",
    secure_work_log: str = "No",
) -> str:
    """Add a work log entry with file attachment to an Incident (WOI:WorkInfo multipart).

    ``file_path`` must be readable by the agent process.

    Parameters
    ----------
    incident_number : str
        Target Incident Number.
    note_text : str
        Work log detailed description text.
    file_path : str
        Local path readable by the agent process.
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
async def close_incident(
    incident_number: str,
    description: str,
    resolution: str = "Solución no especificada",
    intermediate_description: str = "Rest API: Resolve Incident via Mosaico",
    intermediate_status: str | None = DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
    final_status: str = DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
    status_reason: str | None = None,
) -> str:
    """Close an Incident: optional intermediate PUT, then final close PUT.

    Parameters
    ----------
    incident_number : str
        Incident Number to close.
    description : str
        Closure description for the final PUT.
    resolution : str, optional
        Resolution text, by default a placeholder string.
    intermediate_description : str, optional
        Description for optional intermediate PUT.
    intermediate_status : str | None, optional
        Intermediate ``Status`` before close; ``None`` skips the intermediate PUT.
    final_status : str, optional
        Final ``Status`` on close PUT, by default ``'Resolved'``.
    status_reason : str | None, optional
        Status reason when required by BMC characterization.

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
        intermediate_description=intermediate_description,
        intermediate_status=intermediate_status,
        final_status=final_status,
        status_reason=status_reason,
    )
    result = await IncidentOperations(h).close(data)
    return result.model_dump_json()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ALL_BMC_TOOLS: list[BaseTool] = [
    health_check,
    create_work_order,
    get_work_order,
    add_work_order_note,
    add_work_order_attachment,
    update_work_order_status,
    close_work_order,
    create_incident,
    get_incident,
    add_incident_note,
    add_incident_attachment,
    close_incident,
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
