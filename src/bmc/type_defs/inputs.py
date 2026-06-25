"""Input validation models for MCP tool parameters."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from bmc.libs.constants import (
    DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
    DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
    DEFAULT_INCIDENT_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    INCIDENT_STATUSES,
    WORK_ORDER_STATUSES,
)
from bmc.type_defs.ticket_status import (
    validate_incident_status,
    validate_optional_incident_status,
    validate_optional_work_order_status,
    validate_work_order_status,
)

WorkOrderStatusField = Annotated[str, BeforeValidator(validate_work_order_status)]
IncidentStatusField = Annotated[str, BeforeValidator(validate_incident_status)]
OptionalWorkOrderStatusField = Annotated[str | None, BeforeValidator(validate_optional_work_order_status)]
OptionalIncidentStatusField = Annotated[str | None, BeforeValidator(validate_optional_incident_status)]


class WorkOrderIdInput(BaseModel):
    """Input requiring a work order id."""

    work_order_id: str = Field(..., min_length=1, description='Work Order ID (e.g. WO0000000000228).')


class IncidentNumberInput(BaseModel):
    """Input requiring an incident number."""

    incident_number: str = Field(..., min_length=1, description='Incident Number (e.g. INC000000002106).')


class CreateWorkOrderInput(BaseModel):
    """Parameters to create a work order in BMC."""

    company: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    detailed_description: str = Field(..., min_length=1)
    customer_first_name: str = Field(..., min_length=1)
    customer_last_name: str = Field(..., min_length=1)
    customer_company: str = Field(..., min_length=1)
    categorization_tier_1: str = Field(..., min_length=1)
    categorization_tier_2: str = Field(..., min_length=1)
    product_cat_tier_1: str = Field(..., min_length=1)
    product_cat_tier_2: str = Field(..., min_length=1)
    product_cat_tier_3: str = Field(..., min_length=1)
    status: WorkOrderStatusField = Field(
        default=DEFAULT_WORK_ORDER_STATUS,
        json_schema_extra={'enum': list(WORK_ORDER_STATUSES)},
    )
    priority: str = Field(default='Medium')  # TODO: actualizar caracterización


class CreateIncidentInput(BaseModel):
    """Parameters to create an incident in BMC."""

    company: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    detailed_decription: str = Field(..., min_length=1)
    impact: str = Field(default='3-Moderate/Limited')  # TODO: actualizar caracterización
    urgency: str = Field(default='3-Medium')  # TODO: actualizar caracterización
    status: IncidentStatusField = Field(
        default=DEFAULT_INCIDENT_STATUS,
        json_schema_extra={'enum': list(INCIDENT_STATUSES)},
    )
    reported_source: str = Field(default='Direct Input')  # TODO: actualizar caracterización
    service_type: str = Field(default='User Service Restoration')  # TODO: actualizar caracterización
    categorization_tier_1: str = Field(..., min_length=1)
    categorization_tier_2: str = Field(..., min_length=1)
    product_categorization_tier_1: str = Field(..., min_length=1)
    product_categorization_tier_2: str = Field(..., min_length=1)
    product_categorization_tier_3: str = Field(..., min_length=1)
    assigned_group: str = Field(..., min_length=1)  # TODO: actualizar caracterización


class AddWorkOrderNoteInput(WorkOrderIdInput):
    """Add a work log note to a work order."""

    note_text: str = Field(..., min_length=1)
    work_log_type: str = Field(default='General Information')  # TODO: actualizar caracterización
    view_access: str = Field(default='Public')  # TODO: actualizar caracterización
    secure_work_log: str = Field(default='No')  # TODO: actualizar caracterización


class AddWorkOrderAttachmentInput(AddWorkOrderNoteInput):
    """Add a work log note with file attachment to a work order."""

    file_path: str = Field(..., min_length=1, description='Local path readable by the MCP server.')


class AddIncidentNoteInput(IncidentNumberInput):
    """Add a work log note to an incident."""

    note_text: str = Field(..., min_length=1)
    work_log_type: str = Field(default='General Information')  # TODO: actualizar caracterización
    view_access: str = Field(default='Public')  # TODO: actualizar caracterización
    secure_work_log: str = Field(default='No')  # TODO: actualizar caracterización


class AddIncidentAttachmentInput(AddIncidentNoteInput):
    """Add a work log note with file attachment to an incident."""

    file_path: str = Field(..., min_length=1, description='Local path readable by the MCP server.')


class UpdateWorkOrderStatusInput(WorkOrderIdInput):
    """Update work order status (intermediate step)."""

    description: str = Field(..., min_length=1)
    status: WorkOrderStatusField = Field(
        default=DEFAULT_WORK_ORDER_UPDATE_STATUS,
        json_schema_extra={'enum': list(WORK_ORDER_STATUSES)},
    )


class CloseWorkOrderInput(WorkOrderIdInput):
    """Close a work order (orchestrates search + update + close)."""

    description: str = Field(..., min_length=1)
    intermediate_description: str = Field(
        default='Rest API: Resolve WO using RestAPI',
        min_length=1,
    )
    final_description: str = Field(
        default='Rest API: Resolve Work order via Mosaico',
        min_length=1,
    )
    final_status: WorkOrderStatusField = Field(
        default=DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
        json_schema_extra={'enum': list(WORK_ORDER_STATUSES)},
    )
    status_reason: str | None = Field(default=None)  # TODO: actualizar caracterización


class CloseIncidentInput(IncidentNumberInput):
    """Close an incident (orchestrates search + update + close)."""

    description: str = Field(..., min_length=1)
    resolution: str = Field(default='Solución no especificada', min_length=1)
    intermediate_description: str = Field(
        default='Rest API: Resolve Incident via Mosaico',
        min_length=1,
    )
    intermediate_status: OptionalIncidentStatusField = Field(
        default=DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
        json_schema_extra={'enum': list(INCIDENT_STATUSES)},
    )
    final_status: IncidentStatusField = Field(
        default=DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
        json_schema_extra={'enum': list(INCIDENT_STATUSES)},
    )
    status_reason: str | None = Field(default=None)  # TODO: actualizar caracterización
