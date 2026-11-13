"""Modelos de la entrada JSON-RPC A2A (``message/send``)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from type_defs.models.a2a.a2a_protocol import JsonRpcErrorEnvelope, JsonRpcId


@dataclass(frozen=True, slots=True)
class A2AInboundRpcFailure:
    """Respuesta de error lista para serializar como JSON + código HTTP."""

    envelope: JsonRpcErrorEnvelope
    http_status: int


@dataclass(frozen=True, slots=True)
class A2AInboundMessageSendRequest:
    """Entrada validada para ejecutar un turno ``message/send``."""

    req_id: JsonRpcId
    user_text: str
    chat_id: UUID | None
