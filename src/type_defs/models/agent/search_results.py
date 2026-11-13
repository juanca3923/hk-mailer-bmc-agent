"""TypedDicts para los resultados de búsqueda del chat service."""

from __future__ import annotations

from typing import TypedDict


class ChatSearchResult(TypedDict):
    """Resultado de una búsqueda en el historial de chats.

    Retornado por ChatService.search_chats y consumido por las memory tools.
    """

    chat_id: str
    preview: str
    ts: str
    role: str
