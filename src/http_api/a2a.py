"""Protocolo A2A (JSON-RPC) embebido en la misma app FastAPI que POST /chat.

Reutiliza ``app.state.graph`` y ``AgentRunner.run_agent_turn`` para un solo proceso,
misma instancia de grafo y mismas tablas de chat/runs que la API REST.

Soporta ``message/send`` y ``GET /.well-known/agent-card.json``. Otros métodos JSON-RPC
devuelven error estándar sin implementar streaming ni ``tasks/get``.

Parseo y validación JSON-RPC: :mod:`http_api.a2a_jsonrpc`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from agent.runtime.runner import get_agent_runner
from config import Settings, get_logger
from http_api.a2a_jsonrpc import A2AInboundMessageSendProcessor
from http_api.agent_turn_guard import a2a_reserve_turn_or_busy, restore_agent_up_after_turn
from http_api.state import agent_state
from services.persistence.agent_events_service import get_agent_events_service
from type_defs.models.a2a.inbound import A2AInboundMessageSendRequest, A2AInboundRpcFailure

logger = get_logger()

router = APIRouter(tags=["a2a"])


def failure_response(failure: A2AInboundRpcFailure) -> JSONResponse:
    return JSONResponse(failure.envelope, status_code=failure.http_status)


def a2a_preflight_failure(
    proc: A2AInboundMessageSendProcessor,
    req: A2AInboundMessageSendRequest,
    graph: object,
) -> A2AInboundRpcFailure | None:
    """Primer fallo entre grafo, apagado o agente ocupado; None si el turno puede ejecutarse."""
    failure = proc.failure_graph_unavailable(graph, req.req_id)
    if failure is None:
        failure = proc.failure_shutdown_requested(agent_state.shutdown_requested, req.req_id)
    if failure is None:
        failure = a2a_reserve_turn_or_busy(proc.failure_agent_busy(req.req_id))
    return failure


def a2a_message_send_ready(
    proc: A2AInboundMessageSendProcessor,
    parsed: A2AInboundMessageSendRequest | A2AInboundRpcFailure,
    graph: object,
) -> A2AInboundMessageSendRequest | A2AInboundRpcFailure:
    """Validaciones previas al turno; devuelve la petición lista o el fallo JSON-RPC."""
    if isinstance(parsed, A2AInboundRpcFailure):
        return parsed
    failure = a2a_preflight_failure(proc, parsed, graph)
    if failure is not None:
        return failure
    return parsed


@router.get("/.well-known/agent-card.json")
async def agent_card(request: Request, assistant_id: str) -> JSONResponse:
    """Agent Card para descubrimiento (patrón alineado con Agent Server)."""
    settings = Settings.load()
    if not assistant_id.strip():
        raise HTTPException(status_code=400, detail="Falta query assistant_id")
    if assistant_id != settings.effective_a2a_assistant_id:
        raise HTTPException(status_code=404, detail="assistant_id desconocido")
    base = str(request.base_url).rstrip("/")
    card = A2AInboundMessageSendProcessor.build_agent_forge_agent_card(base, settings)
    return JSONResponse(card)


@router.post("/a2a/{assistant_id}")
async def a2a_jsonrpc(
    assistant_id: str,
    request: Request,
) -> JSONResponse:
    """JSON-RPC 2.0; método soportado: ``message/send``."""
    settings = Settings.load()
    if assistant_id != settings.effective_a2a_assistant_id:
        raise HTTPException(status_code=404, detail="assistant_id desconocido")

    raw = await request.body()
    proc = A2AInboundMessageSendProcessor(settings)
    parsed = proc.parse_message_send_from_raw(raw)
    graph = getattr(request.app.state, "graph", None)
    ready = a2a_message_send_ready(proc, parsed, graph)
    if isinstance(ready, A2AInboundRpcFailure):
        return failure_response(ready)
    req = ready

    try:
        logger.info("a2a message/send: texto_len=%d chat_id=%s", len(req.user_text), req.chat_id)
        runner = get_agent_runner()
        result = await runner.run_agent_turn(
            user_message=req.user_text,
            graph=graph,
            chat_id=req.chat_id,
            events_service=get_agent_events_service(),
        )
    finally:
        restore_agent_up_after_turn()

    payload = A2AInboundMessageSendProcessor.build_message_send_success(
        request_id=req.req_id,
        reply=result.reply,
        context_id=str(result.chat_id),
        task_id=str(result.run_id),
        turn_status=result.status,
    )
    return JSONResponse(payload)
