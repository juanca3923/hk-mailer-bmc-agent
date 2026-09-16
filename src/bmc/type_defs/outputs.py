"""Output models returned by MCP tools."""

from pydantic import BaseModel, Field

from bmc.type_defs.ar_api import ArScalarValue


class BaseOutput(BaseModel):
    """Standard MCP tool response with success flag and user message."""

    success: bool = Field(..., description='Whether the operation was successful.')
    message: str = Field(..., description='The message to be displayed to the user.')


class WorkOrderCreatedData(BaseModel):
    """Identifiers returned after creating a work order."""

    work_order_id: str = Field(default='', description='Work Order ID from BMC.')
    request_id: str = Field(default='', description='Request ID from BMC.')


class WorkOrderDetailData(BaseModel):
    """Summary of a work order query result."""

    work_order_id: str = Field(default='')
    request_id: str = Field(default='')
    status: str = Field(default='')
    summary: str = Field(default='')
    values: dict[str, ArScalarValue] = Field(default_factory=dict[str, ArScalarValue])


class IncidentCreatedData(BaseModel):
    """Identifiers returned after creating an incident."""

    incident_number: str = Field(default='')
    description: str = Field(default='')
    categorization_fallback_applied: bool = Field(
        default=False,
        description='Whether the empty-categorization workaround PUT was applied after creation.',
    )


class IncidentDetailData(BaseModel):
    """Summary of an incident query result."""

    incident_number: str = Field(default='')
    request_id: str = Field(default='')
    status: str = Field(default='')
    description: str = Field(default='')
    values: dict[str, ArScalarValue] = Field(default_factory=dict[str, ArScalarValue])


class WorkOrderByEmailRow(BaseModel):
    """One row of a work-order-by-requester-email search result."""

    work_order_id: str = Field(default='')
    status: str = Field(default='')
    summary: str = Field(default='')


class WorkOrdersByEmailData(BaseModel):
    """Result of searching work orders by requester email."""

    email: str = Field(default='')
    total_found: int = Field(default=0, description='Total matches in BMC before capping.')
    returned: int = Field(default=0, description='Number of rows actually returned below.')
    truncated: bool = Field(default=False, description='True when total_found exceeds returned.')
    work_orders: list[WorkOrderByEmailRow] = Field(default_factory=list)


class IncidentByEmailRow(BaseModel):
    """One row of an incident-by-requester-email search result."""

    incident_number: str = Field(default='')
    status: str = Field(default='')
    description: str = Field(default='')


class IncidentsByEmailData(BaseModel):
    """Result of searching incidents by requester email."""

    email: str = Field(default='')
    total_found: int = Field(default=0, description='Total matches in BMC before capping.')
    returned: int = Field(default=0, description='Number of rows actually returned below.')
    truncated: bool = Field(default=False, description='True when total_found exceeds returned.')
    incidents: list[IncidentByEmailRow] = Field(default_factory=list)
