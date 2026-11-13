"""Literales compartidos para estados de runs, mensajes y roles (sin duplicar uniones)."""

from __future__ import annotations

from typing import Final, Literal

# AgentRun.status en BD y dominio
RunStatus = Literal["running", "success", "cancelled", "error"]

# Resultado de un turno (AgentTurnResult, ChatResponse.status)
TurnStatus = Literal["success", "cancelled", "error"]

# ChatStreamDoneEvent.status (subconjunto de TurnStatus sin "error")
StreamDoneStatus = Literal["success", "cancelled"]

# ChatMessage.message_type
MessageType = Literal["normal", "error", "cancelled"]

# ChatMessage.role
ChatRole = Literal["user", "assistant"]

# Constantes en tiempo de ejecución (mismos valores que los Literals anteriores).
# ``Final`` conserva el literal exacto (p. ej. ``Literal['success']``), compatible con ``TurnStatus``.
RUN_STATUS_RUNNING: Final = "running"
RUN_STATUS_SUCCESS: Final = "success"
RUN_STATUS_CANCELLED: Final = "cancelled"
RUN_STATUS_ERROR: Final = "error"

MESSAGE_TYPE_NORMAL: MessageType = "normal"
MESSAGE_TYPE_ERROR: MessageType = "error"
MESSAGE_TYPE_CANCELLED: MessageType = "cancelled"

ROLE_USER: ChatRole = "user"
ROLE_ASSISTANT: ChatRole = "assistant"
