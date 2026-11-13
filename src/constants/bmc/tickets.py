"""Estados, valores por defecto y límites de incidentes y órdenes de trabajo."""

from __future__ import annotations

from typing import Final

from type_defs.enums.bmc_status import IncidentStatus, WorkOrderStatus

MAX_TICKETS_BY_EMAIL_RESULTS: Final[int] = 30


IN_PROGRESS_STATUS: Final[str] = "In Progress"


# HPD:IncidentInterface field "Description" (AR field id 1000000000, shared with
# HPD:IncidentInterface_Create) rejects the request outright above this length:
# "Value does not fall within the limits specified for the field... Maximum length -100".
INCIDENT_DESCRIPTION_MAX_LENGTH: Final[int] = 100


PEOPLE_STATUS_ENABLED: Final[str] = "enabled"


DEFAULT_WORK_LOG_TYPE: Final[str] = "General Information"


DEFAULT_VIEW_ACCESS: Final[str] = "Public"


DEFAULT_SECURE_WORK_LOG: Final[str] = "No"


WORK_ORDER_STATUSES: Final[tuple[str, ...]] = tuple(status.value for status in WorkOrderStatus)


INCIDENT_STATUSES: Final[tuple[str, ...]] = tuple(status.value for status in IncidentStatus)


DEFAULT_WORK_ORDER_STATUS: Final[str] = "Assigned"


DEFAULT_WORK_ORDER_UPDATE_STATUS: Final[str] = IN_PROGRESS_STATUS


DEFAULT_WORK_ORDER_CLOSE_OWNERSHIP_DESCRIPTION: Final[str] = "Rest API: Toma de propiedad previa al cierre"


DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS: Final[str] = "Completed"


DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS: Final[str] = "Closed"


DEFAULT_INCIDENT_STATUS: Final[str] = "Assigned"


DEFAULT_INCIDENT_CLOSE_OWNERSHIP_DESCRIPTION: Final[str] = "Rest API: Toma de propiedad previa al cierre"


DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS: Final[str] = IN_PROGRESS_STATUS


DEFAULT_INCIDENT_CLOSE_FINAL_STATUS: Final[str] = "Resolved"


DEFAULT_INCIDENT_CLOSE_STATUS_REASON: Final[str] = "Closing"


TICKET_STATUS_CLOSED: Final[str] = "Closed"


INCIDENT_FIXED_IMPACT: Final[str] = "1-Extensive/Widespread"


INCIDENT_FIXED_URGENCY: Final[str] = "1-Critical"


# WORKAROUND TEMPORAL: BMC deja vacía la categoría operacional (Categorization Tier 1/2) en
# HPD:IncidentInterface_Create para algunas combinaciones válidas del catálogo Maya, sin lanzar
# error. 'Administracion de TI'/'Seguridad' es la única combinación confirmada manualmente en BMC
# hasta ahora (ver docs/CHANGELOG.md de bmc-mcp). Retirar este default y la verificación asociada en
# IncidentOperations.create() en cuanto BMC/ITSM confirme qué combinaciones acepta el formulario
# de creación.
DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1: Final[str] = "Administracion de TI"


DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_2: Final[str] = "Seguridad"


DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_NOTE: Final[str] = (
    "Rest API: BMC no completó la categoría operacional al crear el incidente. "
    "Se aplicó por defecto Administracion de TI > Seguridad."
)
