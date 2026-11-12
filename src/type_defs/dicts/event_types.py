"""Valores de ``event_type`` para trazas (callbacks → ``agent_events``)."""

from __future__ import annotations

from typing import Final, Literal

# Constantes en tiempo de ejecución (mismos strings que persiste el callback).
# ``Final`` hace que mypy las infiera como ``Literal[...]`` y no como ``str``.
EVENT_LLM_START: Final = "llm_start"
EVENT_LLM_END: Final = "llm_end"
EVENT_LLM_ERROR: Final = "llm_error"
EVENT_TOOL_START: Final = "tool_start"
EVENT_TOOL_END: Final = "tool_end"
EVENT_TOOL_ERROR: Final = "tool_error"

AgentEventType = Literal[
    "llm_start",
    "llm_end",
    "llm_error",
    "tool_start",
    "tool_end",
    "tool_error",
]
