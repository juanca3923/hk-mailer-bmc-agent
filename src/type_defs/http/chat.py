"""Schemas Pydantic para los endpoints de chat."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from type_defs.dicts.domain_literals import TurnStatus


class ChatRequest(BaseModel):
    """Cuerpo de la petición POST /chat."""

    message: str
    # ID del chat existente para continuar una conversación; None crea uno nuevo
    chat_id: UUID | None = None


class ChatResponse(BaseModel):
    """Respuesta de POST /chat."""

    reply: str
    chat_id: UUID
    run_id: UUID
    status: TurnStatus


class ChatMessageResponse(BaseModel):
    """Un mensaje de chat serializado para la API."""

    id: UUID
    role: str
    message_type: str
    content: str
    ts: datetime
    agent_run_id: UUID | None


class ChatSummaryResponse(BaseModel):
    """Resumen de un chat para el listado GET /chats."""

    id: UUID
    created_at: datetime
    last_message_at: datetime
