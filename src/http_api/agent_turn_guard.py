"""Reserva exclusión mutua para un turno del agente (HTTP y A2A inbound).

El candado solo cubre la transición a ``DOING_TASK``; el trabajo del turno corre
fuera del lock (igual que antes). La restauración a ``UP`` va en ``finally`` donde
corresponda (tras ``await`` en /chat y A2A; dentro del generador SSE en /chat/stream).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from commons.a2a_inbound_jsonrpc import A2AInboundRpcFailure
from http_api.state import agent_state


def raise_if_agent_busy_http() -> None:
    """Lanza HTTP 409 si el agente ya está ejecutando una tarea."""
    if agent_state.status == "DOING_TASK":
        raise HTTPException(
            status_code=409,
            detail={"status": "busy", "message": "ocupado realizando una tarea"},
        )


def restore_agent_up_after_turn() -> None:
    """Vuelve el estado operativo a UP si no hay shutdown pendiente."""
    if not agent_state.shutdown_requested:
        agent_state.set_status("UP")


@asynccontextmanager
async def http_turn_claim_and_restore_after_task(fast_app: FastAPI) -> AsyncIterator[None]:
    """Reserva turno para POST /chat: restaura UP al salir del bloque (tras await del turno)."""
    async with fast_app.state.agent_lock:
        raise_if_agent_busy_http()
        agent_state.set_status("DOING_TASK")
    try:
        yield
    finally:
        restore_agent_up_after_turn()


@asynccontextmanager
async def http_turn_claim_for_stream(fast_app: FastAPI) -> AsyncIterator[None]:
    """Reserva turno antes de devolver StreamingResponse; la restauración la hace ``stream_sse``."""
    async with fast_app.state.agent_lock:
        raise_if_agent_busy_http()
        agent_state.set_status("DOING_TASK")
    yield


async def a2a_reserve_turn_or_busy(
    fast_app: FastAPI,
    failure_busy: A2AInboundRpcFailure,
) -> A2AInboundRpcFailure | None:
    """Si hay hueco, pasa a DOING_TASK y retorna None; si está ocupado, retorna ``failure_busy``."""
    async with fast_app.state.agent_lock:
        if agent_state.status == "DOING_TASK":
            return failure_busy
        agent_state.set_status("DOING_TASK")
    return None
