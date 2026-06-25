"""Helpers para el ciclo de vida del agente en el servicio HTTP (FastAPI)."""

from __future__ import annotations

import asyncio
from builtins import BaseExceptionGroup
from contextlib import AsyncExitStack

from fastapi import FastAPI

from agent import build_agent
from config import Settings, get_logger
from http_api.state import agent_state

logger = get_logger()


async def start_agent(
    fast_app: FastAPI,
    stack: AsyncExitStack | None = None,
) -> None:
    """Arranca el agente y lo deja en app.state (stack + graph).
    Si se pasa stack (desde lifespan), se usa; si no, se crea uno (POST /start).
    """
    settings = getattr(fast_app.state, "settings", None) or Settings.load()
    fast_app.state.settings = settings
    if stack is None:
        stack = AsyncExitStack()
        # AsyncExitStack must stay open until stop_agent; async-with would exit too soon.
        await stack.__aenter__()  # noqa: PLC2801  # pylint: disable=unnecessary-dunder-call
    graph = await stack.enter_async_context(build_agent(settings))
    fast_app.state.agent_stack = stack
    fast_app.state.graph = graph
    agent_state.clear_shutdown_requested()
    agent_state.set_status("UP")


def _is_cancel_scope_task_error(exc: BaseException) -> bool:
    """Detecta el error de anyio al cerrar en una tarea distinta a la que abrió."""
    if isinstance(exc, RuntimeError) and "exit cancel scope" in str(exc).lower():
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_cancel_scope_task_error(e) for e in exc.exceptions)
    return False


async def stop_agent(fast_app: FastAPI) -> None:
    """Para el agente y libera recursos (cierra el stack). Cancela chats en curso."""
    chat_tasks: set[asyncio.Task[object]] = getattr(fast_app.state, "chat_tasks", set())
    for task in list(chat_tasks):
        task.cancel()
    stack: AsyncExitStack | None = getattr(fast_app.state, "agent_stack", None)
    fast_app.state.agent_stack = None
    fast_app.state.graph = None
    agent_state.set_status("DOWN")
    if stack is not None:
        try:
            await stack.aclose()
        except (RuntimeError, BaseExceptionGroup) as e:
            if _is_cancel_scope_task_error(e):
                logger.warning(
                    "Cierre del agente desde otra tarea (MCP/anyio): %s. Agente ya DOWN.",
                    e,
                )
            else:
                raise
