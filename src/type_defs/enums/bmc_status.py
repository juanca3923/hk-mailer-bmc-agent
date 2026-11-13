"""BMC ticket status enumerations (selection values sent as ``Status`` in AR API)."""

from enum import StrEnum


class WorkOrderStatus(StrEnum):
    """Work order ``Status`` catalog (WOI)."""

    ASSIGNED = "Assigned"
    PENDING = "Pending"
    WAITING_APPROVAL = "Waiting Approval"
    PLANNING = "Planning"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    CLOSED = "Closed"


class IncidentStatus(StrEnum):
    """Incident ``Status`` catalog (HPD)."""

    NEW = "New"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    PENDING = "Pending"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


WORK_ORDER_STATUSES: tuple[str, ...] = tuple(status.value for status in WorkOrderStatus)
INCIDENT_STATUSES: tuple[str, ...] = tuple(status.value for status in IncidentStatus)


def format_allowed(catalog: tuple[str, ...]) -> str:
    return ", ".join(catalog)


def validate_work_order_status(value: str) -> str:
    """Return *value* if it is a valid work order status label."""
    if value not in WORK_ORDER_STATUSES:
        msg = f"Invalid work order status: {value!r}. Allowed: {format_allowed(WORK_ORDER_STATUSES)}"
        raise ValueError(msg)
    return value


def validate_incident_status(value: str) -> str:
    """Return *value* if it is a valid incident status label."""
    if value not in INCIDENT_STATUSES:
        msg = f"Invalid incident status: {value!r}. Allowed: {format_allowed(INCIDENT_STATUSES)}"
        raise ValueError(msg)
    return value


def validate_optional_work_order_status(value: str | None) -> str | None:
    """Validate optional work order status (``None`` passes through)."""
    if value is None:
        return None
    return validate_work_order_status(value)


def validate_optional_incident_status(value: str | None) -> str | None:
    """Validate optional incident status (``None`` passes through)."""
    if value is None:
        return None
    return validate_incident_status(value)
