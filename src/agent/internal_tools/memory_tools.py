"""Internal memory tools for the LLM to query chats, runs and current state.

All tools are async. Serialization: ``commons.serializers.MemorySerializer``;
queries: ``services.agent_runs_service.AgentRunsService`` and ``ChatService``.
"""

from __future__ import annotations

import json

from langchain_core.tools import BaseTool, tool

from commons.serializers import MemorySerializer
from commons.utils import parse_uuid_param
from config import get_logger
from services.agent_runs_service import get_agent_runs_service
from services.chat_service import get_chat_service

logger = get_logger()


@tool
async def memory_get_current_task() -> str:
    """Consulta si el agente tiene una tarea activa en este momento.

    Retorna un JSON con el run en curso (status=running) o indica que no hay
    ninguna tarea activa. Útil para responder '¿qué estás haciendo ahora mismo?'
    """
    logger.debug("memory_get_current_task: consultando runs activos")
    active_run = await get_agent_runs_service().get_active_run()

    if active_run is None:
        logger.debug("memory_get_current_task: sin tarea activa")
        return json.dumps({"active_task": None, "message": "No hay ninguna tarea activa."})

    logger.info("memory_get_current_task: tarea activa run=%s", active_run.id)
    return json.dumps(
        {
            "active_task": MemorySerializer.run(active_run),
            "message": f"Hay una tarea activa: '{active_run.user_message[:120]}'",
        }
    )


@tool
async def memory_search_chats(query: str) -> str:
    """Busca en el historial de chats mensajes que contengan el texto indicado.

    Args:
        query: Texto a buscar (no distingue mayúsculas/minúsculas).

    Retorna un JSON con lista de chats que tuvieron conversaciones relacionadas,
    incluyendo un preview del mensaje que hizo match y la fecha.
    Útil cuando el usuario pregunta 'recuerdas cuando hablamos de X'.
    """
    logger.info("memory_search_chats: query=%r", query)
    results = await get_chat_service().search_chats(query, limit=10)

    if not results:
        return json.dumps({"found": [], "message": f"No se encontraron chats con '{query}'."})

    return json.dumps(
        {
            "found": results,
            "count": len(results),
            "message": f"Se encontraron {len(results)} chat(s) con '{query}'.",
        }
    )


@tool
async def memory_get_chat_messages(chat_id: str, limit: int = 20) -> str:
    """Recupera el historial de mensajes de un chat específico.

    Args:
        chat_id: UUID del chat (obtenido previamente con memory_search_chats).
        limit: Número máximo de mensajes a retornar (default 20).

    Retorna un JSON con la lista de mensajes en orden cronológico,
    incluyendo role, contenido y tipo (normal/error/cancelled).
    """
    logger.info("memory_get_chat_messages: chat_id=%s limit=%d", chat_id, limit)
    parsed = parse_uuid_param(chat_id, "chat_id")
    if isinstance(parsed, str):
        return json.dumps({"error": parsed})

    messages = await get_chat_service().get_all_messages(parsed, limit=limit)
    if not messages:
        return json.dumps({"messages": [], "message": f"El chat {chat_id} no tiene mensajes."})

    return json.dumps(
        {
            "chat_id": chat_id,
            "messages": [MemorySerializer.chat_message(m) for m in messages],
            "total": len(messages),
        }
    )


@tool
async def memory_list_recent_runs(limit: int = 10) -> str:
    """Lista las últimas ejecuciones del agente con su resumen.

    Args:
        limit: Número de runs a retornar (default 10, máximo 50).

    Retorna un JSON con los runs más recientes ordenados por fecha de inicio
    descendente, incluyendo el mensaje del usuario, estado y preview de la respuesta.
    """
    safe_limit = min(limit, 50)
    logger.info("memory_list_recent_runs: limit=%d", safe_limit)
    runs = await get_agent_runs_service().list_recent_runs(safe_limit)

    if not runs:
        return json.dumps({"runs": [], "message": "No hay ejecuciones registradas."})

    return json.dumps(
        {
            "runs": [MemorySerializer.run(r) for r in runs],
            "total": len(runs),
        }
    )


@tool
async def memory_get_run_events(run_id: str) -> str:
    """Obtiene la traza detallada de una ejecución: cada llamada LLM y herramienta usada.

    Args:
        run_id: UUID del run (obtenido con memory_list_recent_runs).

    Retorna un JSON con los eventos ordenados cronológicamente: llm_start,
    tool_start, tool_end, llm_end, etc. Útil para explicar en detalle qué hizo
    el agente en una ejecución específica.
    """
    logger.info("memory_get_run_events: run_id=%s", run_id)
    parsed = parse_uuid_param(run_id, "run_id")
    if isinstance(parsed, str):
        return json.dumps({"error": parsed})

    result = await get_agent_runs_service().get_run_with_events(parsed)
    if result is None:
        return json.dumps({"error": f"Run {run_id} no encontrado."})

    run, events = result
    return json.dumps(
        {
            "run": MemorySerializer.run(run),
            "events": [MemorySerializer.event(e) for e in events],
            "total_events": len(events),
        }
    )


def get_memory_tools() -> list[BaseTool]:
    """Retorna la lista de tools internas de memoria para pasarlas al agente."""
    return [
        memory_get_current_task,
        memory_search_chats,
        memory_get_chat_messages,
        memory_list_recent_runs,
        memory_get_run_events,
    ]
