"""Shared type definitions for bmc-mcp."""

from bmc.type_defs.json_types import JsonValue
from bmc.type_defs.outputs import (
    BaseOutput,
    IncidentCreatedData,
    IncidentDetailData,
    WorkOrderCreatedData,
    WorkOrderDetailData,
)

__all__ = [
    'BaseOutput',
    'IncidentCreatedData',
    'IncidentDetailData',
    'JsonValue',
    'WorkOrderCreatedData',
    'WorkOrderDetailData',
]
