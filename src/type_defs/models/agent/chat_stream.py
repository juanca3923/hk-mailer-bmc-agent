"""Eventos de streaming de chat (SSE) — tipos de alambre servidor → cliente."""

from __future__ import annotations

import json
from typing import Literal, TypedDict, cast

from type_defs.enums.domain_literals import StreamDoneStatus


class ChatStreamChunkEvent(TypedDict):
    """Fragmento de texto del modelo (delta)."""

    type: Literal["chunk"]
    text: str


class ChatStreamDoneEvent(TypedDict):
    """Fin de turno con metadatos alineados a la respuesta HTTP de /chat."""

    type: Literal["done"]
    chat_id: str
    run_id: str
    status: StreamDoneStatus
    reply: str


class ChatStreamErrorEvent(TypedDict):
    """Error controlado tras persistencia del turno (detalle visible)."""

    type: Literal["error"]
    detail: str


ChatStreamServerEvent = ChatStreamChunkEvent | ChatStreamDoneEvent | ChatStreamErrorEvent


def chat_stream_event_to_json_line(event: ChatStreamServerEvent) -> str:
    """Serializa un evento a una línea JSON (sin prefijo ``data:`` ni CRLF)."""
    payload: dict[str, object] = cast(dict[str, object], event)
    return json.dumps(payload, ensure_ascii=False)
