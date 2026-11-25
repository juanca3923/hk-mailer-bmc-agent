"""Mensajes de error para el usuario de las herramientas de BMC."""

from __future__ import annotations

from typing import Final

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


NOT_VERIFIED_MARKER: Final[str] = "Estado final: No verificado"


USER_ERROR_MESSAGE_PERSON_NOT_FOUND: Final[str] = (
    NOT_VERIFIED_MARKER + " — no hay ninguna persona registrada en BMC con el correo {email}. "
    "No se creó el ticket. Es definitivo: no reintentes ni busques otra forma de crearlo."
)
