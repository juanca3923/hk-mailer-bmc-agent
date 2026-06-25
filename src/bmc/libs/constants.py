"""Shared constants for bmc-mcp (no env-specific secrets)."""

from typing import Final

READ_TIMEOUT_SECONDS: Final[float] = 30.0

API_PATH_JWT_LOGIN: Final[str] = '/api/jwt/login'
API_PATH_JWT_LOGOUT: Final[str] = '/api/jwt/logout'
API_PATH_ARSYS_ENTRY_PREFIX: Final[str] = '/api/arsys/v1/entry'

HEADER_CONTENT_TYPE_JSON: Final[str] = 'application/json'
HEADER_X_REQUESTED_BY: Final[str] = 'XMLHttpRequest'
HEADER_AUTHORIZATION_PREFIX: Final[str] = 'AR-JWT'

COOKIE_AR_JWT: Final[str] = 'AR-JWT'

AR_FIELD_WORK_ORDER_ID: Final[str] = 'Work Order ID'
AR_FIELD_ASSIGNEE: Final[str] = 'Assignee'
AR_FIELD_INCIDENT_NUMBER: Final[str] = 'Incident Number'
AR_FIELD_REQUEST_ID: Final[str] = 'Request ID'
AR_FIELD_WORK_ORDER_ID_RESPONSE: Final[str] = 'WorkOrder_ID'

AR_ACTION_CREATE: Final[str] = 'CREATE'
AR_Z1D_ACTION_CREATE: Final[str] = 'CREATE'
AR_Z1D_ACTION_FIELD_WO: Final[str] = 'z1D_Action'
AR_Z1D_ACTION_FIELD_WORK_INFO: Final[str] = 'z1D Action'

WORK_LOG_ATTACHMENT_FIELD: Final[str] = 'z2AF Work Log01'
WORK_LOG_ATTACHMENT_MARKER: Final[str] = 'adjunto'
MULTIPART_PART_ENTRY: Final[str] = 'entry'
MULTIPART_ENTRY_CONTENT_TYPE: Final[str] = 'application/json'
MULTIPART_ATTACH_PREFIX: Final[str] = 'attach-'

DEFAULT_WORK_LOG_TYPE: Final[str] = 'General Information'  # TODO: actualizar caracterización
DEFAULT_VIEW_ACCESS: Final[str] = 'Public'  # TODO: actualizar caracterización
DEFAULT_SECURE_WORK_LOG: Final[str] = 'No'  # TODO: actualizar caracterización

WORK_ORDER_STATUSES: Final[tuple[str, ...]] = (
    'Assigned',
    'Pending',
    'Waiting Approval',
    'Planning',
    'In Progress',
    'Completed',
    'Rejected',
    'Cancelled',
    'Closed',
)

INCIDENT_STATUSES: Final[tuple[str, ...]] = (
    'New',
    'Assigned',
    'In Progress',
    'Pending',
    'Resolved',
    'Closed',
    'Cancelled',
)

DEFAULT_WORK_ORDER_STATUS: Final[str] = 'Assigned'
DEFAULT_WORK_ORDER_UPDATE_STATUS: Final[str] = 'In Progress'
DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS: Final[str] = 'Completed'
DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS: Final[str] = 'Closed'

DEFAULT_INCIDENT_STATUS: Final[str] = 'Assigned'
DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS: Final[str] = 'In Progress'
DEFAULT_INCIDENT_CLOSE_FINAL_STATUS: Final[str] = 'Resolved'

MIN_REFRESH_LOOP_SECONDS: Final[int] = 60

USER_ERROR_MESSAGES: Final[dict[int, str]] = {
    401: 'Error: Sesión BMC inválida o expirada. Comprueba BMC_USERNAME y BMC_PASSWORD.',
    403: 'Error: Permiso denegado en BMC para esta operación.',
    404: 'Error: Recurso no encontrado en BMC. Comprueba el identificador del ticket.',
    409: 'Error: Conflicto en BMC. El ticket puede estar en un estado incompatible.',
    429: 'Error: Límite de peticiones excedido en BMC. Espera antes de reintentar.',
}

USER_ERROR_MESSAGE_TIMEOUT: Final[str] = 'Error: La petición a BMC ha tardado demasiado. Inténtalo de nuevo.'
USER_ERROR_MESSAGE_NETWORK: Final[str] = 'Error: No se pudo contactar con BMC. Comprueba BMC_BASE_URL y la red.'
USER_ERROR_MESSAGE_INVALID_JSON: Final[str] = 'Error: La respuesta de BMC no es JSON válido.'
USER_ERROR_MESSAGE_UNEXPECTED: Final[str] = 'Error inesperado en la operación BMC. Revisa los logs para más detalles.'
USER_ERROR_MESSAGE_LOGIN_FAILED: Final[str] = (
    'Error: No se pudo autenticar en BMC al arrancar. El servidor MCP no se inicia.'
)
USER_ERROR_MESSAGE_WRITE_DISABLED: Final[str] = (
    'Error: Las operaciones de escritura están deshabilitadas (BMC_ALLOW_WRITE=false).'
)
USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE: Final[str] = 'Error: El adjunto supera el tamaño máximo permitido.'
USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND: Final[str] = 'Error: No se encontró el archivo adjunto en la ruta indicada.'
USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND: Final[str] = 'Error: WO no encontrada: {work_order_id}.'
USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING: Final[str] = 'Error: Request ID no disponible en la WO.'
USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND: Final[str] = 'Error: Incidente no encontrado: {incident_number}.'
USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING: Final[str] = 'Error: Request ID no disponible en el incidente.'
