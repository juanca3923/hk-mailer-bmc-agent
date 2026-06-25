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


class IncidentDetailData(BaseModel):
    """Summary of an incident query result."""

    incident_number: str = Field(default='')
    request_id: str = Field(default='')
    status: str = Field(default='')
    description: str = Field(default='')
    values: dict[str, ArScalarValue] = Field(default_factory=dict[str, ArScalarValue])
