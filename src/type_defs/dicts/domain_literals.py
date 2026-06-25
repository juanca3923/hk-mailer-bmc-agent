"""Literales compartidos para estados de runs, mensajes y roles (sin duplicar uniones)."""

from __future__ import annotations

from typing import Literal

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

# Constantes en tiempo de ejecución (mismos valores que los Literals anteriores)
RUN_STATUS_RUNNING: RunStatus = "running"
RUN_STATUS_SUCCESS: RunStatus = "success"
RUN_STATUS_CANCELLED: RunStatus = "cancelled"
RUN_STATUS_ERROR: RunStatus = "error"

MESSAGE_TYPE_NORMAL: MessageType = "normal"
MESSAGE_TYPE_ERROR: MessageType = "error"
MESSAGE_TYPE_CANCELLED: MessageType = "cancelled"

ROLE_USER: ChatRole = "user"
ROLE_ASSISTANT: ChatRole = "assistant"
