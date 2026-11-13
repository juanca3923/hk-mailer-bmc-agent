"""Callback handler que instrumenta una ejecución del agente asociada a agent_run_id."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from agent.observability.interceptor_helpers import InterceptorHelpers
from commons.text.utils import TextUtils
from config import get_logger
from exception import AgentError
from services.persistence.agent_events_service import AgentEventsService
from type_defs.enums.event_types import (
    EVENT_LLM_END,
    EVENT_LLM_ERROR,
    EVENT_LLM_START,
    EVENT_TOOL_END,
    EVENT_TOOL_ERROR,
    EVENT_TOOL_START,
    AgentEventType,
)
from type_defs.models.agent.event_payloads import (
    LlmEndPayload,
    LlmErrorPayload,
    LlmStartPayload,
    ToolEndPayload,
    ToolErrorPayload,
    ToolStartPayload,
)
from type_defs.models.common.json_types import JsonDict
from type_defs.ports.agent import LogFn

logger = get_logger()


class AgentRunCallbackHandler(AsyncCallbackHandler):
    """Callback handler que instrumenta una ejecución del agente asociada a agent_run_id.

    Persiste eventos (llm_start, llm_end, tool_start, tool_end, etc.) en la BD
    a través de AgentEventsService, y/o los emite a una función de logging externa.
    """

    def __init__(
        self,
        *,
        agent_run_id: UUID,
        events_service: AgentEventsService | None = None,
        log_fn: LogFn | None = None,
        payload_limit_chars: int = 50000,
    ) -> None:
        super().__init__()
        self.agent_run_id = agent_run_id
        self.payload_limit_chars = payload_limit_chars
        self._events_service = events_service
        self._log_fn = log_fn
        self._tool_starts: dict[str, float] = {}
        self._tool_names: dict[str, str] = {}
        self._helpers = InterceptorHelpers()

    @classmethod
    def build_callbacks(
        cls,
        agent_run_id: UUID,
        events_service: AgentEventsService,
    ) -> list[AgentRunCallbackHandler]:
        """Crea la lista de handlers de instrumentación para un agent_run_id."""
        logger.debug(
            "build_callbacks: run_id=%s events_service=%s",
            agent_run_id,
            type(events_service).__name__,
        )
        return [cls(agent_run_id=agent_run_id, events_service=events_service)]

    # ------------------------------------------------------------------
    # Emisión de eventos
    # ------------------------------------------------------------------

    async def _emit(self, event_type: AgentEventType, event_payload: Mapping[str, object]) -> None:
        # Los payloads son TypedDict; se pasan como ``dict`` plano a persistencia y logging.
        payload: JsonDict = dict(event_payload)
        if self._events_service is not None:
            try:
                await self._events_service.insert_event(
                    agent_run_id=self.agent_run_id,
                    event_type=event_type,
                    payload=payload,
                )
            except AgentError as error:
                logger.error("Error insertando evento %s: %s", event_type, type(error).__name__)
                return

        if self._log_fn is not None:
            self._log_fn(event_type=event_type, agent_run_id=self.agent_run_id, payload=payload)

    # ------------------------------------------------------------------
    # Callbacks de LLM
    # ------------------------------------------------------------------

    async def on_chat_model_start(
        self,
        serialized: JsonDict,
        messages: list[list[BaseMessage]],
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        metadata: object = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        model = serialized.get("name")
        serialized_id = serialized.get("id")
        if not model and isinstance(serialized_id, list) and len(serialized_id) > 0:
            model = serialized_id[-1]
        step = None
        if isinstance(metadata, dict):
            step = metadata.get("langgraph_step")
        human_message, ai_message = self._helpers.extract_last_human_and_ai_messages(messages)
        tool_results = self._helpers.extract_trailing_tool_results_for_llm_start(messages)
        payload: LlmStartPayload = {
            "model": cast("str | None", model),
            "human_message": human_message,
            "ai_message": ai_message,
        }
        if step is not None:
            payload["step"] = step
        if tool_results:
            payload["tool_results"] = tool_results
        logger.info("llm_start: run=%s model=%r", self.agent_run_id, model)
        await self._emit(EVENT_LLM_START, payload)

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        input_tokens, output_tokens = self._helpers.extract_usage_tokens(response)
        logger.info(
            "run=%s %s",
            self.agent_run_id,
            self._helpers.summarize_llm_end_for_logging(
                response,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                preview_limit=0,
            ),
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "run=%s %s",
                self.agent_run_id,
                self._helpers.summarize_llm_end_for_logging(
                    response,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    preview_limit=200,
                ),
            )
        if self._helpers.llm_result_has_suspicious_empty_message(response):
            logger.warning(
                "LLM devolvió content vacío y tool_calls=[] (run %s); el grafo puede no terminar o devolver fallback",
                self.agent_run_id,
            )
        llm_response = self._helpers.extract_llm_response_content(response)
        payload: LlmEndPayload = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        if llm_response is not None:
            payload["llm_response"] = llm_response
        await self._emit(EVENT_LLM_END, payload)

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        err_str = TextUtils.truncate(repr(error), self._helpers.ERROR_TRUNCATE_CHARS)
        logger.error("llm_error: run=%s error=%s", self.agent_run_id, type(error).__name__)
        logger.debug("llm_error: run=%s detail=%s", self.agent_run_id, TextUtils.truncate(err_str, 200))
        payload: LlmErrorPayload = {"error": err_str}
        await self._emit(EVENT_LLM_ERROR, payload)

    # ------------------------------------------------------------------
    # Callbacks de tools
    # ------------------------------------------------------------------

    async def on_tool_start(
        self,
        serialized: JsonDict,
        input_str: str,
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        metadata: object = None,
        inputs: JsonDict | None = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        sid = serialized.get("id")
        tool_name = serialized.get("name") or (sid if isinstance(sid, str) else None)
        input_params = inputs if isinstance(inputs, dict) else None
        tool_call_id = kwargs.get("tool_call_id")
        if tool_call_id is not None:
            self._tool_starts[str(tool_call_id)] = time.monotonic()
            self._tool_names[str(tool_call_id)] = str(tool_name)
        payload: ToolStartPayload = {"tool_name": cast("str | None", tool_name), "input": input_params or {}}
        if tool_call_id is not None:
            payload["tool_call_id"] = str(tool_call_id)
        # Tool arguments carry emails and free text: INFO only gets the argument names and sizes.
        logger.info(
            "tool_start: run=%s tool=%s args=%s",
            self.agent_run_id,
            tool_name,
            sorted(input_params) if input_params else [],
        )
        logger.debug("tool_start: run=%s tool=%s input_chars=%d", self.agent_run_id, tool_name, len(input_str))
        await self._emit(EVENT_TOOL_START, payload)

    async def on_tool_end(
        self,
        output: object,
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        tool_call_id = kwargs.get("tool_call_id")
        duration_seconds: float | None = None
        if tool_call_id is not None:
            start = self._tool_starts.pop(str(tool_call_id), None)
            if start is not None:
                duration_seconds = time.monotonic() - start
        result = self._helpers.tool_result_summary(output, self._helpers.RESULT_TRUNCATE_CHARS)
        payload: ToolEndPayload = {
            "result": result,
            "duration_seconds": duration_seconds,
        }
        logger.info(
            "tool_end: run=%s tool=%s duration=%.3fs",
            self.agent_run_id,
            self._tool_names.pop(str(tool_call_id), None),
            duration_seconds or 0.0,
        )
        await self._emit(EVENT_TOOL_END, payload)

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: object,
        parent_run_id: object = None,
        tags: object = None,
        **kwargs: Any,  # noqa: ANN401 — firma impuesta por AsyncCallbackHandler
    ) -> None:
        tool_call_id = kwargs.get("tool_call_id")
        duration_seconds: float | None = None
        if tool_call_id is not None:
            start = self._tool_starts.pop(str(tool_call_id), None)
            if start is not None:
                duration_seconds = time.monotonic() - start
        err_str = TextUtils.truncate(repr(error), self._helpers.ERROR_TRUNCATE_CHARS)
        payload: ToolErrorPayload = {"error": err_str}
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        logger.warning(
            "tool_error: run=%s tool=%s duration=%.3fs error=%s",
            self.agent_run_id,
            self._tool_names.pop(str(tool_call_id), None),
            duration_seconds or 0.0,
            type(error).__name__,
        )
        logger.debug("tool_error: run=%s detail=%s", self.agent_run_id, TextUtils.truncate(err_str, 200))
        await self._emit(EVENT_TOOL_ERROR, payload)
