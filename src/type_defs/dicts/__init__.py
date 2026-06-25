"""TypedDicts, Protocols, dataclasses y aliases de tipo para AgentForge."""

from __future__ import annotations

from type_defs.dicts.a2a import PeerInfo
from type_defs.dicts.agent_memory import AgentEventSummary, AgentRunSummary, ChatMessageSummary
from type_defs.dicts.agent_turn import AgentTurnResult, TurnContext
from type_defs.dicts.chat_stream import (
    ChatStreamChunkEvent,
    ChatStreamDoneEvent,
    ChatStreamErrorEvent,
    ChatStreamServerEvent,
    chat_stream_event_to_json_line,
)
from type_defs.dicts.domain_literals import (
    MESSAGE_TYPE_CANCELLED,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_NORMAL,
    ROLE_ASSISTANT,
    ROLE_USER,
    RUN_STATUS_CANCELLED,
    RUN_STATUS_ERROR,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    ChatRole,
    MessageType,
    RunStatus,
    StreamDoneStatus,
    TurnStatus,
)
from type_defs.dicts.event_payloads import (
    LlmEndPayload,
    LlmErrorPayload,
    LlmStartPayload,
    ToolEndPayload,
    ToolErrorPayload,
    ToolResultLogEntry,
    ToolStartPayload,
)
from type_defs.dicts.event_types import (
    EVENT_LLM_END,
    EVENT_LLM_ERROR,
    EVENT_LLM_START,
    EVENT_TOOL_END,
    EVENT_TOOL_ERROR,
    EVENT_TOOL_START,
    AgentEventType,
)
from type_defs.dicts.json_types import JsonDict
from type_defs.dicts.protocols import LogFn
from type_defs.dicts.search_results import ChatSearchResult
from type_defs.dicts.skill_catalog import SkillCatalogEntry
from type_defs.dicts.store import MemoryFactEntry, MemoryFactSearchResult

__all__ = [
    "PeerInfo",
    "AgentEventType",
    "AgentEventSummary",
    "AgentRunSummary",
    "AgentTurnResult",
    "ChatStreamChunkEvent",
    "ChatStreamDoneEvent",
    "ChatStreamErrorEvent",
    "ChatStreamServerEvent",
    "ChatMessageSummary",
    "ChatSearchResult",
    "SkillCatalogEntry",
    "chat_stream_event_to_json_line",
    "JsonDict",
    "LlmEndPayload",
    "LlmErrorPayload",
    "LlmStartPayload",
    "LogFn",
    "MemoryFactEntry",
    "MemoryFactSearchResult",
    "ToolEndPayload",
    "ToolErrorPayload",
    "ToolResultLogEntry",
    "ToolStartPayload",
    "TurnContext",
    "ChatRole",
    "EVENT_LLM_END",
    "EVENT_LLM_ERROR",
    "EVENT_LLM_START",
    "EVENT_TOOL_END",
    "EVENT_TOOL_ERROR",
    "EVENT_TOOL_START",
    "MESSAGE_TYPE_CANCELLED",
    "MESSAGE_TYPE_ERROR",
    "MESSAGE_TYPE_NORMAL",
    "MessageType",
    "ROLE_ASSISTANT",
    "ROLE_USER",
    "RUN_STATUS_CANCELLED",
    "RUN_STATUS_ERROR",
    "RUN_STATUS_RUNNING",
    "RUN_STATUS_SUCCESS",
    "RunStatus",
    "StreamDoneStatus",
    "TurnStatus",
]
