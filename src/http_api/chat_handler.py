"""Helpers del endpoint HTTP de chat."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException

from commons.runner import get_agent_runner
from config import get_logger
from http_api.agent_turn_guard import (
    http_turn_claim_and_restore_after_task,
    raise_if_agent_busy_http,
    restore_agent_up_after_turn,
)
from http_api.state import agent_state
from services.agent_events_service import get_agent_events_service
from type_defs import ChatRequest, ChatResponse, chat_stream_event_to_json_line

logger = get_logger()


class ChatHandler:
    """Agrupa los helpers internos del endpoint POST /chat."""

    @staticmethod
    async def run_registered_turn(fast_app: FastAPI, body: ChatRequest, graph: object) -> ChatResponse:
        """POST /chat: reserva turno, ejecuta en tarea registrada y restaura UP al terminar."""
        async with http_turn_claim_and_restore_after_task(fast_app):
            chat_tasks: set[asyncio.Task[object]] = getattr(fast_app.state, "chat_tasks", set())
            task: asyncio.Task[ChatResponse] = asyncio.create_task(ChatHandler.execute(body, graph))
            chat_tasks.add(task)
            try:
                return await task
            finally:
                chat_tasks.discard(task)

    @staticmethod
    def get_graph_or_raise(fast_app: FastAPI) -> object:
        """Retorna el grafo del agente o lanza HTTPException 503 si no está disponible."""
        graph = getattr(fast_app.state, "graph", None)
        if graph is None:
            raise HTTPException(status_code=503, detail="Agente no disponible")
        return graph

    @staticmethod
    def check_shutdown_or_raise() -> None:
        """Lanza HTTPException 503 si el agente está en proceso de parada."""
        if agent_state.shutdown_requested:
            raise HTTPException(status_code=503, detail="Servicio en proceso de parada")

    @staticmethod
    def check_not_busy_or_raise() -> None:
        """Lanza HTTPException 409 si el agente ya está ejecutando una tarea."""
        raise_if_agent_busy_http()

    @staticmethod
    async def execute(
        body: ChatRequest,
        graph: object,
    ) -> ChatResponse:
        """Ejecuta el turno de chat dentro de la task cancelable."""
        logger.info("chat: iniciando turno mensaje_len=%d", len(body.message))
        runner = get_agent_runner()
        result = await runner.run_agent_turn(
            user_message=body.message,
            graph=graph,
            chat_id=body.chat_id,
            events_service=get_agent_events_service(),
        )
        logger.info(
            "chat: turno completado run=%s chat=%s status=%s",
            result.run_id,
            result.chat_id,
            result.status,
        )
        return ChatResponse(
            reply=result.reply,
            chat_id=result.chat_id,
            run_id=result.run_id,
            status=result.status,
        )

    @staticmethod
    async def stream_sse(
        body: ChatRequest,
        graph: object,
    ) -> AsyncIterator[bytes]:
        """Itera eventos del turno en streaming y los emite como líneas SSE (UTF-8)."""
        runner = get_agent_runner()
        events_svc = get_agent_events_service()
        try:
            async for event in runner.stream_agent_turn(
                user_message=body.message,
                graph=graph,
                chat_id=body.chat_id,
                events_service=events_svc,
            ):
                line = "data: " + chat_stream_event_to_json_line(event) + "\n\n"
                yield line.encode("utf-8")
        finally:
            restore_agent_up_after_turn()
