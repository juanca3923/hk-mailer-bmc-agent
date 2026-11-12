"""TypedDicts para los payloads de eventos que se persisten en agent_events."""

from __future__ import annotations

from typing import TypedDict

from type_defs.dicts.json_types import JsonDict


class ToolResultLogEntry(TypedDict, total=False):
    """Una salida de herramienta registrada en llm_start (contexto previo al modelo)."""

    tool_name: str | None
    tool_call_id: str
    content: str | None


class LlmStartPayload(TypedDict, total=False):
    """Payload del evento llm_start. Campos que se persisten en DB."""

    model: str | None
    step: int | str
    human_message: str | None
    ai_message: str | None
    tool_results: list[ToolResultLogEntry]


class LlmEndPayload(TypedDict, total=False):
    """Payload del evento llm_end. Campos que se persisten en DB."""

    input_tokens: int
    output_tokens: int
    llm_response: str | None


class LlmErrorPayload(TypedDict):
    """Payload del evento llm_error. Campos que se persisten en DB."""

    error: str


class ToolStartPayload(TypedDict, total=False):
    """Payload del evento tool_start. Campos que se persisten en DB."""

    tool_name: str | None
    input: JsonDict
    tool_call_id: str


class ToolEndPayload(TypedDict):
    """Payload del evento tool_end. Campos que se persisten en DB."""

    result: str | JsonDict | None
    duration_seconds: float | None


class ToolErrorPayload(TypedDict, total=False):
    """Payload del evento tool_error. Campos que se persisten en DB."""

    error: str
    duration_seconds: float
