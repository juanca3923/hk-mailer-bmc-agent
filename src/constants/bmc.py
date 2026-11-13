"""Shared constants for bmc-mcp (no env-specific secrets)."""

from typing import Final

READ_TIMEOUT_SECONDS: Final[float] = 30.0
MAX_TICKETS_BY_EMAIL_RESULTS: Final[int] = 30
IN_PROGRESS_STATUS: Final[str] = "In Progress"
DETAIL_DESCRIPTION_FIELD: Final[str] = "Detailed Description"
CATEGORIZATION_TIER_1_FIELD: Final[str] = "Categorization Tier 1"
CATEGORIZATION_TIER_2_FIELD: Final[str] = "Categorization Tier 2"

API_PATH_JWT_LOGIN: Final[str] = "/api/jwt/login"
API_PATH_JWT_LOGOUT: Final[str] = "/api/jwt/logout"
API_PATH_ARSYS_ENTRY_PREFIX: Final[str] = "/api/arsys/v1/entry"

HEADER_CONTENT_TYPE_JSON: Final[str] = "application/json"
HEADER_X_REQUESTED_BY: Final[str] = "XMLHttpRequest"
HEADER_AUTHORIZATION_PREFIX: Final[str] = "AR-JWT"

COOKIE_AR_JWT: Final[str] = "AR-JWT"

AR_FIELD_WORK_ORDER_ID: Final[str] = "Work Order ID"
AR_FIELD_ASSIGNEE: Final[str] = "Assignee"
AR_FIELD_INCIDENT_NUMBER: Final[str] = "Incident Number"
AR_FIELD_REQUEST_ID: Final[str] = "Request ID"
AR_FIELD_WORK_ORDER_ID_RESPONSE: Final[str] = "WorkOrder_ID"
AR_FIELD_STATUS: Final[str] = "Status"
AR_FIELD_SUBMITTER: Final[str] = "Submitter"
AR_FIELD_CATEGORIZATION_TIER_1: Final[str] = "Categorization Tier 1"
AR_FIELD_CATEGORIZATION_TIER_2: Final[str] = "Categorization Tier 2"

# HPD:IncidentInterface field "Description" (AR field id 1000000000, shared with
# HPD:IncidentInterface_Create) rejects the request outright above this length:
# "Value does not fall within the limits specified for the field... Maximum length -100".
INCIDENT_DESCRIPTION_MAX_LENGTH: Final[int] = 100

# CTM:People (reporter identity lookup by email — see services.bmc.person_lookup)
AR_FIELD_PEOPLE_LOGIN_ID: Final[str] = "Remedy Login ID"
AR_FIELD_PEOPLE_FIRST_NAME: Final[str] = "First Name"
AR_FIELD_PEOPLE_LAST_NAME: Final[str] = "Last Name"
AR_FIELD_PEOPLE_EMAIL: Final[str] = "Internet E-mail"
# Whether the person is active ("Enabled"; other values: "Offline", "Obsolete", ...). The field name is
# not in BMC's public docs and still has to be confirmed against the real instance (GET a person
# without ``fields`` and look for the one that says "Enabled"); this is the only place it is defined.
AR_FIELD_PEOPLE_STATUS: Final[str] = "Profile Status"
PEOPLE_STATUS_ENABLED: Final[str] = "enabled"

# Requester-email fields used to list tickets by requester (verified empirically
# against BMC: each form stores the raw reporter_email in a different field — WO
# keeps it on the fixed "Customer" identity's email field, INC keeps it on its own
# "Internet E-mail"; neither is the CTM:People-resolved login id).
AR_FIELD_WO_CUSTOMER_EMAIL: Final[str] = "Customer Internet E-mail"
AR_FIELD_INCIDENT_REPORTER_EMAIL: Final[str] = "Internet E-mail"

# Assigned-group fields for reading back a ticket's current group (not the same field
# used to *set* it at creation). For incidents, "Assigned Group" round-trips correctly —
# same alias as CreateIncidentValues.assigned_group. For work orders, the create-time
# alias ("Support Group Name", CreateWorkOrderValues.assigned_group) does NOT round-trip:
# verified empirically against BMC that reading it back always shows the fixed desk
# default ("SOPORTE MESA DE SERVICIO") regardless of what was requested at creation,
# while "ASGRP" (BMC's internal assignment-engine field) does reflect the real group.
AR_FIELD_WORK_ORDER_ASGRP: Final[str] = "ASGRP"
AR_FIELD_INCIDENT_ASSIGNED_GROUP: Final[str] = "Assigned Group"

AR_ACTION_CREATE: Final[str] = "CREATE"
AR_Z1D_ACTION_CREATE: Final[str] = "CREATE"
AR_Z1D_ACTION_FIELD_WO: Final[str] = "z1D_Action"
AR_Z1D_ACTION_FIELD_WORK_INFO: Final[str] = "z1D Action"

WORK_LOG_ATTACHMENT_FIELD: Final[str] = "z2AF Work Log01"
WORK_LOG_ATTACHMENT_MARKER: Final[str] = "adjunto"
MULTIPART_PART_ENTRY: Final[str] = "entry"
MULTIPART_ENTRY_CONTENT_TYPE: Final[str] = "application/json"
MULTIPART_ATTACH_PREFIX: Final[str] = "attach-"

DEFAULT_WORK_LOG_TYPE: Final[str] = "General Information"
DEFAULT_VIEW_ACCESS: Final[str] = "Public"
DEFAULT_SECURE_WORK_LOG: Final[str] = "No"

WORK_ORDER_STATUSES: Final[tuple[str, ...]] = (
    "Assigned",
    "Pending",
    "Waiting Approval",
    "Planning",
    IN_PROGRESS_STATUS,
    "Completed",
    "Rejected",
    "Cancelled",
    "Closed",
)

INCIDENT_STATUSES: Final[tuple[str, ...]] = (
    "New",
    "Assigned",
    IN_PROGRESS_STATUS,
    "Pending",
    "Resolved",
    "Closed",
    "Cancelled",
)

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

MIN_REFRESH_LOOP_SECONDS: Final[int] = 60

USER_ERROR_MESSAGES: Final[dict[int, str]] = {
    401: "Error: Sesión BMC inválida o expirada. Comprueba BMC_USERNAME y BMC_PASSWORD.",
    403: "Error: Permiso denegado en BMC para esta operación.",
    404: "Error: Recurso no encontrado en BMC. Comprueba el identificador del ticket.",
    409: "Error: Conflicto en BMC. El ticket puede estar en un estado incompatible.",
    429: "Error: Límite de peticiones excedido en BMC. Espera antes de reintentar.",
}

USER_ERROR_MESSAGE_TIMEOUT: Final[str] = "Error: La petición a BMC ha tardado demasiado. Inténtalo de nuevo."
USER_ERROR_MESSAGE_NETWORK: Final[str] = "Error: No se pudo contactar con BMC. Comprueba BMC_BASE_URL y la red."
USER_ERROR_MESSAGE_INVALID_JSON: Final[str] = "Error: La respuesta de BMC no es JSON válido."
USER_ERROR_MESSAGE_UNEXPECTED: Final[str] = "Error inesperado en la operación BMC. Revisa los logs para más detalles."
USER_ERROR_MESSAGE_LOGIN_FAILED: Final[str] = (
    "Error: No se pudo autenticar en BMC al arrancar. El servidor MCP no se inicia."
)
USER_ERROR_MESSAGE_WRITE_DISABLED: Final[str] = (
    "Error: Las operaciones de escritura están deshabilitadas (BMC_ALLOW_WRITE=false)."
)
USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE: Final[str] = "Error: El adjunto supera el tamaño máximo permitido."
USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND: Final[str] = "Error: No se encontró el archivo adjunto en la ruta indicada."
USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED: Final[str] = (
    "Error: El archivo está fuera de la carpeta de adjuntos permitida y no se puede adjuntar."
)
USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED: Final[str] = (
    "Error: Los adjuntos no están habilitados (BMC_ATTACHMENT_BASE_DIR sin configurar)."
)
USER_ERROR_MESSAGE_STAGING_INVALID_ID: Final[str] = "Error: El staging_id no es válido."
USER_ERROR_MESSAGE_STAGING_NOT_FOUND: Final[str] = "Error: No se encontró la carpeta de archivos indicada."
USER_ERROR_MESSAGE_STAGING_INVALID_MANIFEST: Final[str] = (
    "Error: El manifiesto de archivos falta o es inválido."
)
USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND: Final[str] = "Error: WO no encontrada: {work_order_id}."
USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING: Final[str] = "Error: Request ID no disponible en la WO."
USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND: Final[str] = "Error: Incidente no encontrado: {incident_number}."
USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING: Final[str] = "Error: Request ID no disponible en el incidente."
USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED: Final[str] = (
    "Error: El ticket ya está Cerrado. No se permiten operaciones de escritura sobre él."
)
USER_ERROR_MESSAGE_CLOSE_NOT_OWNER: Final[str] = (
    "Error: Solo el usuario de servicio de este agente puede cerrar este ticket. Submitter actual: {submitter}."
)
USER_ERROR_MESSAGE_PERSON_NOT_FOUND: Final[str] = (
    "Error: No se encontró en BMC ninguna persona registrada con el correo {email}. No se creó el ticket."
)
