"""Reserva/registra el estado DOING_TASK/UP de un turno (HTTP y A2A inbound).

Por defecto (``HTTP_ALLOW_CONCURRENT_TURNS=1``) ``agent_state`` permite turnos
concurrentes. Con la variable en ``0`` es un run por turno: un turno nuevo se rechaza
mientras haya uno en curso. En ambos casos ``try_begin_task``/``end_task`` llevan la
cuenta, así que el estado solo vuelve a UP cuando termina el último turno en curso.
``try_begin_task`` no tiene ningún ``await`` de por medio, así que es atómico sin
necesidad de un lock explícito.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException

from commons.a2a_inbound_jsonrpc import A2AInboundRpcFailure
from http_api.state import agent_state


def reserve_turn_or_raise_http() -> None:
    """Reserva el turno; lanza HTTP 409 si ya hay uno en curso y no se permiten concurrentes."""
    if not agent_state.try_begin_task():
        raise HTTPException(
            status_code=409,
            detail={"status": "busy", "message": "ocupado realizando una tarea"},
        )


def restore_agent_up_after_turn() -> None:
    """Registra el fin de un turno; vuelve a UP solo si no queda ninguno en curso."""
    agent_state.end_task()


@asynccontextmanager
async def http_turn_claim_and_restore_after_task() -> AsyncIterator[None]:
    """Reserva turno para POST /chat: restaura estado al salir del bloque (tras await del turno)."""
    reserve_turn_or_raise_http()
    try:
        yield
    finally:
        restore_agent_up_after_turn()


@asynccontextmanager
async def http_turn_claim_for_stream() -> AsyncIterator[None]:
    """Reserva turno para POST /chat/stream; la restauración la hace ``stream_sse``."""
    reserve_turn_or_raise_http()
    yield


def a2a_reserve_turn_or_busy(failure_busy: A2AInboundRpcFailure) -> A2AInboundRpcFailure | None:
    """Si hay hueco, reserva el turno y retorna None; si está ocupado, retorna ``failure_busy``."""
    if not agent_state.try_begin_task():
        return failure_busy
    return None
