"""Tipos de AgentForge — todo el tipado del proyecto concentrado aquí.

Subcarpetas:
- ``type_defs/http/``   : modelos Pydantic (``BaseModel``) para contratos HTTP.
- ``type_defs/dicts/``  : ``TypedDict``, ``Protocol``, dataclasses y aliases.

Importar desde el módulo concreto (p. ej. ``type_defs.dicts.json_types``) o desde
este paquete cuando convenga ``from type_defs import ...``. Las re-exportaciones de
``dicts`` y ``http`` se definen solo en sus ``__init__.py`` (sin duplicar rutas aquí).
"""

from __future__ import annotations

from type_defs.dicts import (
    EVENT_LLM_END,
    EVENT_LLM_ERROR,
    EVENT_LLM_START,
    EVENT_TOOL_END,
    EVENT_TOOL_ERROR,
    EVENT_TOOL_START,
    MESSAGE_TYPE_CANCELLED,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_NORMAL,
    ROLE_ASSISTANT,
    ROLE_USER,
    RUN_STATUS_CANCELLED,
    RUN_STATUS_ERROR,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    AgentEventSummary,
    AgentEventType,
    AgentRunSummary,
    AgentTurnResult,
    ChatMessageSummary,
    ChatRole,
    ChatSearchResult,
    ChatStreamChunkEvent,
    ChatStreamDoneEvent,
    ChatStreamErrorEvent,
    ChatStreamServerEvent,
    JsonDict,
    LlmEndPayload,
    LlmErrorPayload,
    LlmStartPayload,
    LogFn,
    MemoryFactEntry,
    MemoryFactSearchResult,
    MessageType,
    PeerInfo,
    RunStatus,
    SkillCatalogEntry,
    StreamDoneStatus,
    ToolEndPayload,
    ToolErrorPayload,
    ToolResultLogEntry,
    ToolStartPayload,
    TurnContext,
    TurnStatus,
    chat_stream_event_to_json_line,
)
from type_defs.dicts import __all__ as _dicts_all
from type_defs.http import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSummaryResponse,
    EventDetail,
    RunDetailResponse,
    RunTokensSummary,
    StatsResponse,
    StatusAgent,
    StatusResponse,
)
from type_defs.http import __all__ as _http_all

__all__ = list(_dicts_all) + list(_http_all)
