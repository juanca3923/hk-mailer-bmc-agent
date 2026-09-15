"""BMC AR API ``values`` payloads (Pydantic; field aliases match AR names)."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from bmc.libs.constants import (
    CATEGORIZATION_TIER_1_FIELD,
    CATEGORIZATION_TIER_2_FIELD,
    DEFAULT_INCIDENT_STATUS,
    DEFAULT_WORK_ORDER_STATUS,
    DETAIL_DESCRIPTION_FIELD,
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
        return {"values": dumped}


class CreateWorkOrderValues(BaseModel):
    """Required fields for ``WOI:WorkOrderInterface_Create`` (see ``docs/BMC_API.md``)."""

    model_config = ConfigDict(populate_by_name=True)

    company: str = Field(alias="Company")
    first_name: str = Field(alias="First Name")
    last_name: str = Field(alias="Last Name")
    summary: str = Field(alias="Summary")
    detailed_description: str = Field(alias=DETAIL_DESCRIPTION_FIELD)
    status: WorkOrderStatusField = Field(default=DEFAULT_WORK_ORDER_STATUS, alias="Status")
    z1d_action: str = Field(default="CREATE", alias="z1D_Action")
    customer_first_name: str = Field(alias="Customer First Name")
    customer_last_name: str = Field(alias="Customer Last Name")
    customer_company: str = Field(alias="Customer Company")
    categorization_tier_1: str = Field(alias=CATEGORIZATION_TIER_1_FIELD)
    categorization_tier_2: str = Field(alias=CATEGORIZATION_TIER_2_FIELD)
    product_cat_tier_1: str = Field(alias="Product Cat Tier 1(2)")
    product_cat_tier_2: str = Field(alias="Product Cat Tier 2 (2)")
    product_cat_tier_3: str = Field(alias="Product Cat Tier 3 (2)")
    priority: str = Field(default="Medium", alias="Priority")
    support_company: str = Field(alias="Support Company")
    support_organization: str = Field(alias="Support Organization")
    assigned_group: str = Field(alias="Support Group Name")


class CreateIncidentValues(BaseModel):
    """Required fields for ``HPD:IncidentInterface_Create`` (see ``docs/BMC_API.md``)."""

    model_config = ConfigDict(populate_by_name=True)

    company: str = Field(alias="Company")
    first_name: str = Field(alias="First_Name")
    last_name: str = Field(alias="Last_Name")
    description: str = Field(alias="Description")
    impact: str = Field(alias="Impact")
    urgency: str = Field(alias="Urgency")
    status: IncidentStatusField = Field(default=DEFAULT_INCIDENT_STATUS, alias="Status")
    reported_source: str = Field(alias="Reported Source")
    service_type: str = Field(alias="Service_Type")
    detailed_decription: str = Field(alias="Detailed_Decription")
    categorization_tier_1: str = Field(default="", alias=CATEGORIZATION_TIER_1_FIELD)
    categorization_tier_2: str = Field(default="", alias=CATEGORIZATION_TIER_2_FIELD)
    product_categorization_tier_1: str = Field(alias="Product Categorization Tier 1")
    product_categorization_tier_2: str = Field(alias="Product Categorization Tier 2")
    product_categorization_tier_3: str = Field(alias="Product Categorization Tier 3")
    assigned_support_company: str = Field(alias="Assigned Support Company")
    assigned_support_organization: str = Field(alias="Assigned Support Organization")
    assigned_group: str = Field(alias="Assigned Group")


class UpdateWorkOrderStatusValues(BaseModel):
    """Intermediate PUT before closing a work order."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias="Description")
    status: WorkOrderStatusField = Field(alias="Status")
    aschg: str | None = Field(default=None, alias="ASCHG")


class UpdateIncidentStatusValues(BaseModel):
    """Intermediate PUT before closing an incident."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias="Description")
    status: IncidentStatusField = Field(alias="Status")
    assignee: str | None = Field(default=None, alias="Assignee")


class UpdateIncidentCategorizationValues(BaseModel):
    """PUT patch for the operational-category fallback workaround (see ``IncidentOperations``)."""

    model_config = ConfigDict(populate_by_name=True)

    categorization_tier_1: str = Field(alias=CATEGORIZATION_TIER_1_FIELD)
    categorization_tier_2: str = Field(alias=CATEGORIZATION_TIER_2_FIELD)


class CloseWorkOrderValues(BaseModel):
    """Final close PUT for work order."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias="Description")
    status: OptionalWorkOrderStatusField = Field(default=None, alias="Status")


class CloseIncidentValues(BaseModel):
    """Close PUT for incident."""

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(alias="Description")
    resolution: str | None = Field(default=None, alias="Resolution")
    status: OptionalIncidentStatusField = Field(default=None, alias="Status")
    status_reason: str | None = Field(default=None, alias="Status_Reason")


class WorkInfoWorkOrderValues(BaseModel):
    """Work log entry for a work order (``WOI:WorkInfo``)."""

    model_config = ConfigDict(populate_by_name=True)

    work_order_id: str = Field(alias="Work Order ID")
    z1d_action: str = Field(default="CREATE", alias="z1D Action")
    work_log_type: str = Field(
        default="General Information",
        alias="Work Log Type",
    )
    view_access: str = Field(default="Public", alias="View Access")
    secure_work_log: str = Field(default="No", alias="Secure Work Log")
    detailed_description: str = Field(alias=DETAIL_DESCRIPTION_FIELD)
    attachment_marker: str | None = Field(default=None, alias="z2AF Work Log01")


class WorkInfoIncidentValues(BaseModel):
    """Work log entry for an incident (``WOI:WorkInfo``)."""

    model_config = ConfigDict(populate_by_name=True)

    incident_number: str = Field(alias="Incident Number")
    z1d_action: str = Field(default="CREATE", alias="z1D Action")
    work_log_type: str = Field(
        default="General Information",
        alias="Work Log Type",
    )
    view_access: str = Field(default="Public", alias="View Access")
    secure_work_log: str = Field(default="No", alias="Secure Work Log")
    detailed_description: str = Field(alias=DETAIL_DESCRIPTION_FIELD)
    attachment_marker: str | None = Field(default=None, alias="z2AF Work Log01")
