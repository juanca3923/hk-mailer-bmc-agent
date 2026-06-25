"""TypedDicts para los resultados serializados de MemorySerializer.

Representan la estructura exacta de los dicts que las memory tools
construyen para enviar al LLM como contexto JSON.
"""

from __future__ import annotations

from typing import TypedDict


class AgentRunSummary(TypedDict):
    """Resumen serializado de un AgentRun para el contexto del LLM."""

    id: str
    chat_id: str | None
    status: str
    user_message: str
    final_reply: str | None
    started_at: str | None
    ended_at: str | None
    total_time_seconds: float | None
    error_text: str | None


class AgentEventSummary(TypedDict):
    """Resumen serializado de un AgentEvent para el contexto del LLM."""

    event_type: str
    ts: str
    payload_summary: dict[str, object]


class ChatMessageSummary(TypedDict):
    """Resumen serializado de un ChatMessage para el contexto del LLM."""

    role: str
    message_type: str
    content: str
    ts: str
    agent_run_id: str | None
