"""Valores de ``event_type`` para trazas (callbacks → ``agent_events``)."""

from __future__ import annotations

from typing import Literal

# Constantes en tiempo de ejecución (mismos strings que persiste el callback)
EVENT_LLM_START = "llm_start"
EVENT_LLM_END = "llm_end"
EVENT_LLM_ERROR = "llm_error"
EVENT_TOOL_START = "tool_start"
EVENT_TOOL_END = "tool_end"
EVENT_TOOL_ERROR = "tool_error"

AgentEventType = Literal[
    "llm_start",
    "llm_end",
    "llm_error",
    "tool_start",
    "tool_end",
    "tool_error",
]
