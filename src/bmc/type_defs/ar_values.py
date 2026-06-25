"""BMC AR API ``values`` payloads (Pydantic; field aliases match AR names)."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from bmc.libs.constants import DEFAULT_INCIDENT_STATUS, DEFAULT_WORK_ORDER_STATUS
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


class BmcValuesBody(BaseModel):
    """Wrapper for POST/PUT bodies: ``{"values": {...}}``."""

    model_config = ConfigDict(populate_by_name=True)

    values: BaseModel

    def to_api_dict(self) -> dict[str, object]:
        """Serialize to the BMC API JSON body shape.

        Returns
        -------
        dict[str, object]
            Body of the form ``{"values": {...}}`` with AR field aliases.
        """
        dumped = self.values.model_dump(by_alias=True, exclude_none=True)
        return {'values': dumped}


class CreateWorkOrderValues(BaseModel):
    """Required fields for ``WOI:WorkOrderInterface_Create`` (see ``docs/BMC_API.md``)."""

    model_config = ConfigDict(populate_by_name=True)

    company: str = Field(alias='Company')
    first_name: str = Field(alias='First Name')
    last_name: str = Field(alias='Last Name')
    summary: str = Field(alias='Summary')
    detailed_description: str = Field(alias='Detailed Description')
    status: WorkOrderStatusField = Field(default=DEFAULT_WORK_ORDER_STATUS, alias='Status')
    z1d_action: str = Field(default='CREATE', alias='z1D_Action')
    customer_first_name: str = Field(alias='Customer First Name')
    customer_last_name: str = Field(alias='Customer Last Name')
    customer_company: str = Field(alias='Customer Company')
    categorization_tier_1: str = Field(alias='Categorization Tier 1')
    categorization_tier_2: str = Field(alias='Categorization Tier 2')
    product_cat_tier_1: str = Field(alias='Product Cat Tier 1(2)')
    product_cat_tier_2: str = Field(alias='Product Cat Tier 2 (2)')
    product_cat_tier_3: str = Field(alias='Product Cat Tier 3 (2)')
    priority: str = Field(default='Medium', alias='Priority')  # TODO: actualizar caracterización


class CreateIncidentValues(BaseModel):
    """Required fields for ``HPD:IncidentInterface_Create`` (see ``docs/BMC_API.md``)."""

    model_config = ConfigDict(populate_by_name=True)

    company: str = Field(alias='Company')
    first_name: str = Field(alias='First_Name')
    last_name: str = Field(alias='Last_Name')
    description: str = Field(alias='Description')
    impact: str = Field(alias='Impact')  # TODO: actualizar caracterización
    urgency: str = Field(alias='Urgency')  # TODO: actualizar caracterización
    status: IncidentStatusField = Field(default=DEFAULT_INCIDENT_STATUS, alias='Status')
    reported_source: str = Field(alias='Reported Source')  # TODO: actualizar caracterización
    service_type: str = Field(alias='Service_Type')  # TODO: actualizar caracterización
    detailed_decription: str = Field(alias='Detailed_Decription')
    categorization_tier_1: str = Field(alias='Categorization Tier 1')
    categorization_tier_2: str = Field(alias='Categorization Tier 2')
    product_categorization_tier_1: str = Field(alias='Product Categorization Tier 1')
    product_categorization_tier_2: str = Field(alias='Product Categorization Tier 2')
    product_categorization_tier_3: str = Field(alias='Product Categorization Tier 3')
    assigned_group: str = Field(alias='Assigned Group')  # TODO: actualizar caracterización


class UpdateWorkOrderStatusValues(BaseModel):
    """Intermediate PUT before closing a work order."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias='Description')
    status: WorkOrderStatusField = Field(alias='Status')
    assignee: str | None = Field(default=None, alias='Assignee')


class UpdateIncidentStatusValues(BaseModel):
    """Intermediate PUT before closing an incident."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias='Description')
    status: IncidentStatusField = Field(alias='Status')


class CloseWorkOrderValues(BaseModel):
    """Final close PUT for work order."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias='Description')
    status: OptionalWorkOrderStatusField = Field(default=None, alias='Status')
    status_reason: str | None = Field(default=None, alias='Status Reason')  # TODO: actualizar caracterización


class CloseIncidentValues(BaseModel):
    """Close PUT for incident."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias='Description')
    resolution: str | None = Field(default=None, alias='Resolution')
    status: OptionalIncidentStatusField = Field(default=None, alias='Status')
    status_reason: str | None = Field(default=None, alias='Status Reason')  # TODO: actualizar caracterización


class WorkInfoWorkOrderValues(BaseModel):
    """Work log entry for a work order (``WOI:WorkInfo``)."""

    model_config = ConfigDict(populate_by_name=True)

    work_order_id: str = Field(alias='Work Order ID')
    z1d_action: str = Field(default='CREATE', alias='z1D Action')
    work_log_type: str = Field(
        default='General Information',
        alias='Work Log Type',
    )  # TODO: actualizar caracterización
    view_access: str = Field(default='Public', alias='View Access')  # TODO: actualizar caracterización
    secure_work_log: str = Field(default='No', alias='Secure Work Log')  # TODO: actualizar caracterización
    detailed_description: str = Field(alias='Detailed Description')
    attachment_marker: str | None = Field(default=None, alias='z2AF Work Log01')


class WorkInfoIncidentValues(BaseModel):
    """Work log entry for an incident (``WOI:WorkInfo``)."""

    model_config = ConfigDict(populate_by_name=True)

    incident_number: str = Field(alias='Incident Number')
    z1d_action: str = Field(default='CREATE', alias='z1D Action')
    work_log_type: str = Field(
        default='General Information',
        alias='Work Log Type',
    )  # TODO: actualizar caracterización
    view_access: str = Field(default='Public', alias='View Access')  # TODO: actualizar caracterización
    secure_work_log: str = Field(default='No', alias='Secure Work Log')  # TODO: actualizar caracterización
    detailed_description: str = Field(alias='Detailed Description')
    attachment_marker: str | None = Field(default=None, alias='z2AF Work Log01')
