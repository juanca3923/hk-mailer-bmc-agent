"""Internal memory tools for the LLM to query chats, runs and current state.

All tools are async. Serialization: ``services.persistence.memory_serializer.MemorySerializer``;
queries: ``services.persistence.agent_runs_service.AgentRunsService`` and ``ChatService``.
"""

from __future__ import annotations

import json
from typing import Annotated

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from commons.text.utils import parse_uuid_param
from config import get_logger
from services.persistence.agent_runs_service import get_agent_runs_service
from services.persistence.chat_service import get_chat_service
from services.persistence.memory_serializer import MemorySerializer

logger = get_logger()


@tool(
    description=(
        "Check whether the agent currently has an active task in progress. Use this "
        "to answer 'what are you doing right now?' or 'are you busy?'."
    )
)
async def memory_get_current_task() -> str:
    """Check whether the agent currently has an active task in progress.

    Useful for answering "what are you doing right now?". Returns a JSON with the
    run in progress (status=running), or indicates there is none.
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


@tool(
    description=(
        "Search the chat history for messages containing the given text — for finding "
        "a past conversation the user vaguely references (e.g. 'remember when we "
        "talked about X'). Never use this to silently source a business identifier "
        "(ticket, order, record) a write tool needs and the user did not give in the "
        "current conversation — only after they confirm they mean a previous one."
    )
)
async def memory_search_chats(
    query: Annotated[
        str,
        Field(
            min_length=1,
            description="Text to search for across the chat history (case-insensitive substring match).",
        ),
    ],
) -> str:
    """Search the chat history for messages containing the given text.

    Useful when the user asks something like "do you remember when we talked about
    X". Returns a JSON list of chats with a matching conversation, including a
    preview of the matched message and its date.

    Never call this to silently source a business identifier (ticket, order, record)
    that a write tool needs and the user did not give in the current conversation —
    only to answer the user's own explicit question about past activity, after they
    confirm they mean a previous conversation.
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


@tool(
    description=(
        "Retrieve the full message history of one chat, in chronological order. Never "
        "use this to silently source a business identifier (ticket, order, record) for "
        "a write tool the user did not explicitly ask you to look up in a past chat."
    )
)
async def memory_get_chat_messages(
    chat_id: Annotated[
        str,
        Field(min_length=1, description="UUID of the chat, previously obtained from memory_search_chats."),
    ],
    limit: Annotated[int, Field(description="Maximum number of messages to return.")] = 20,
) -> str:
    """Retrieve the message history of one chat, in chronological order.

    Each message includes role, content and type (normal/error/cancelled).

    Never call this to silently source a business identifier (ticket, order, record)
    for a write tool the user did not explicitly ask you to look up in a past chat.
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


@tool(
    description=(
        "List the agent's most recent runs with a short summary of each (capped at "
        "50). Never use this to guess which ticket/resource a write tool should act on "
        "when the current conversation has none — only to answer the user's own "
        "question about recent activity, or after they confirm they mean a previous "
        "conversation."
    )
)
async def memory_list_recent_runs(
    limit: Annotated[
        int,
        Field(
            description=(
                "Number of runs to return; silently capped at 50 by this tool regardless of "
                "the value requested."
            ),
        ),
    ] = 10,
) -> str:
    """List the agent's most recent runs with a short summary of each.

    Ordered by start date, most recent first. Each entry includes the user
    message, status and a preview of the response.

    Never call this to guess which ticket/resource a write tool should act on when
    the current conversation has none — a run from a different chat is not this
    conversation's context. Only use it to answer the user's own question about
    recent activity, or after they confirm they mean a previous conversation.
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


@tool(
    description=(
        "Retrieve the detailed step-by-step trace of one run (every LLM call and tool "
        "call, in order). Use it when the user wants to know exactly what happened "
        "during a specific execution."
    )
)
async def memory_get_run_events(
    run_id: Annotated[
        str,
        Field(min_length=1, description="UUID of the run, previously obtained from memory_list_recent_runs."),
    ],
) -> str:
    """Retrieve the detailed trace of one run: every LLM call and tool call used.

    Events come in chronological order (llm_start, tool_start, tool_end, llm_end,
    etc.). Useful for explaining in detail what the agent did during that run.
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
    """Return the internal memory tools to register on the agent."""
    return [
        memory_get_current_task,
        memory_search_chats,
        memory_get_chat_messages,
        memory_list_recent_runs,
        memory_get_run_events,
    ]
