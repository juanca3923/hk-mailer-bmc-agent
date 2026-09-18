"""Rutas REST principales: estado, chat, consultas y ciclo de vida del agente."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from commons.agent_http import start_agent, stop_agent
from config import get_logger
from exception import AgentError
from http_api.agent_turn_guard import http_turn_claim_for_stream
from http_api.chat_handler import ChatHandler
from http_api.state import agent_state
from services.agent_runs_service import AgentRunsService, get_agent_runs_service
from services.agent_runs_stats_service import get_agent_runs_stats_service
from services.chat_service import get_chat_service
from type_defs import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSummaryResponse,
    EventDetail,
    RunDetailResponse,
    StatsResponse,
    StatusResponse,
)

logger = get_logger()

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Devuelve el estado actual del agente (DOWN, UP, DOING_TASK)."""
    return StatusResponse(status=agent_state.status)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Envía un mensaje al agente y devuelve la respuesta."""
    graph = ChatHandler.get_graph_or_raise(request.app)
    ChatHandler.check_shutdown_or_raise()
    return await ChatHandler.run_registered_turn(request.app, body, graph)


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest) -> StreamingResponse:
    """Envía un mensaje al agente y devuelve la respuesta como SSE."""
    graph = ChatHandler.get_graph_or_raise(request.app)
    ChatHandler.check_shutdown_or_raise()
    logger.info("chat/stream: iniciando turno mensaje_len=%d", len(body.message))

    async with http_turn_claim_for_stream():
        return StreamingResponse(
            ChatHandler.stream_sse(body, graph),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


@router.get("/runs/last", response_model=RunDetailResponse)
async def get_last_run() -> RunDetailResponse:
    """Devuelve el detalle de la última run y sus eventos."""
    agent_runs_service: AgentRunsService = get_agent_runs_service()
    result = await agent_runs_service.get_last_run_with_events()
    if result is None:
        raise HTTPException(status_code=404, detail="No hay ninguna run")
    run_data, events = result
    return RunDetailResponse(
        id=str(run_data.id),
        started_at=run_data.started_at,
        ended_at=run_data.ended_at,
        total_time=run_data.total_time,
        user_message=run_data.user_message,
        final_reply=run_data.final_reply,
        status=run_data.status,
        error_text=run_data.error_text,
        total_input_tokens=run_data.total_input_tokens,
        total_output_tokens=run_data.total_output_tokens,
        events=[EventDetail(event_type=e.event_type, ts=e.ts, payload=e.payload) for e in events],
    )


@router.get("/runs/stats", response_model=StatsResponse)
async def get_runs_stats() -> StatsResponse:
    """Estadísticas agregadas: tokens de entrada/salida y tiempo promedio."""
    stats_service = get_agent_runs_stats_service()
    data = await stats_service.get_token_and_time_stats()
    return StatsResponse(**data)


@router.get("/chats", response_model=list[ChatSummaryResponse])
async def list_chats() -> list[ChatSummaryResponse]:
    """Lista los chats más recientes ordenados por último mensaje."""
    chats = await get_chat_service().list_recent_chats(limit=50)
    return [
        ChatSummaryResponse(
            id=chat.id,
            created_at=chat.created_at,
            last_message_at=chat.last_message_at,
        )
        for chat in chats
    ]


@router.get("/chats/{chat_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_messages(chat_id: UUID) -> list[ChatMessageResponse]:
    """Devuelve el historial completo de un chat."""
    messages = await get_chat_service().get_all_messages(chat_id, limit=200)
    if not messages:
        raise HTTPException(status_code=404, detail="Chat no encontrado o sin mensajes")
    return [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            message_type=m.message_type,
            content=m.content,
            ts=m.ts,
            agent_run_id=m.agent_run_id,
        )
        for m in messages
    ]


@router.post("/start")
async def start(request: Request) -> JSONResponse:
    """Arranca el agente (grafo y MCP). Si ya está UP, no hace nada y devuelve 200."""
    if agent_state.status == "UP":
        return JSONResponse(
            status_code=200,
            content={"status": "UP", "message": "Agente ya en marcha"},
        )
    try:
        await start_agent(request.app)
        return JSONResponse(
            status_code=200,
            content={"status": "UP", "message": "Agente iniciado"},
        )
    except AgentError as e:
        logger.exception("Error al iniciar el agente")
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/stop")
async def stop(request: Request) -> JSONResponse:
    """Para el agente y libera recursos. Servidor sigue; usa POST /start para reiniciar."""
    agent_state.request_shutdown()
    await stop_agent(request.app)
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "message": "Agente detenido"},
    )
