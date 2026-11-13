"""Tests de flujo conversacional con GenericFakeChatModel sin consumir tokens.

Incluye un caso que pasa por ``AgentRunCallbackHandler`` igual que CLI/HTTP
(mismo handler + ``insert_event``), usando un mock de ``AgentEventsService``
para no requerir Postgres.
"""

from __future__ import annotations

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from agent.interceptors.agent_run_callback import AgentRunCallbackHandler
from services.persistence.agent_events_service import AgentEventsService


def _get_server_status(server_name: str) -> dict[str, object]:
    """Simula una tool de monitoreo de servidor."""
    return {
        "server": server_name,
        "status": "up",
        "cpu_percent": 38,
        "memory_percent": 67,
        "active_alerts": 0,
    }


async def _get_server_status_tool_acoro(server: str) -> str:
    """Implementación async para que ``StructuredTool.ainvoke`` use callbacks async (como en grafo)."""
    return json.dumps(_get_server_status(server))


async def _run_server_status_chat_flow(
    model: GenericFakeChatModel,
    *,
    user_question: str,
    callbacks: list[AgentRunCallbackHandler] | None = None,
) -> tuple[AIMessage, AIMessage]:
    """Ejecuta un flujo simple: pregunta -> tool call -> respuesta final."""
    config: dict[str, object] = {}
    if callbacks is not None:
        config["callbacks"] = callbacks

    messages: list[HumanMessage | AIMessage | ToolMessage] = [HumanMessage(content=user_question)]

    first_ai = await model.ainvoke(messages, config=config or None)
    messages.append(first_ai)

    for tool_call in first_ai.tool_calls:
        tool_result = _get_server_status(tool_call["args"]["server"])
        messages.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )

    second_ai = await model.ainvoke(messages, config=config or None)
    return first_ai, second_ai


@pytest.mark.asyncio
async def test_fake_llm_flow_server_status_with_tool_call_and_summary() -> None:
    model = GenericFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "reasoning_content": (
                            "Para responder con precisión, primero debo consultar la "
                            "tool de estado del servidor."
                        )
                    },
                    tool_calls=[
                        {
                            "name": "get_server_status",
                            "args": {"server": "server-x"},
                            "id": "call_server_status_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(
                    content=(
                        "Resumen de estado de server-x: el servidor está UP, CPU en 38%, "
                        "memoria en 67% y no hay alertas activas."
                    )
                ),
            ]
        )
    )

    first_ai, second_ai = await _run_server_status_chat_flow(
        model,
        user_question="¿Cuál es el estado del servidor server-x?",
    )

    # Valida que el modelo "razona" y decide usar una tool antes de responder.
    reasoning_content = (first_ai.additional_kwargs or {}).get("reasoning_content")
    assert isinstance(reasoning_content, str) and reasoning_content.strip()
    assert len(first_ai.tool_calls) == 1
    assert first_ai.tool_calls[0]["name"] == "get_server_status"
    assert first_ai.tool_calls[0]["args"] == {"server": "server-x"}

    # Valida el resumen final basado en el resultado simulado de la tool.
    assert isinstance(second_ai.content, str)
    assert "server-x" in second_ai.content
    assert "UP" in second_ai.content
    assert "38%" in second_ai.content
    assert "67%" in second_ai.content


@pytest.mark.asyncio
async def test_fake_llm_flow_with_agent_run_callback_handler_like_runner() -> None:
    """Mismo wiring que ``build_graph_invoke_config``: callbacks en ``ainvoke``/tool.

    ``AgentEventsService`` está mockeado (sin BD); se verifica la secuencia de
    ``insert_event`` (llm_start/llm_end/tool_start/tool_end) como en HTTP/CLI.
    """
    run_id = uuid4()
    events_mock = MagicMock(spec=AgentEventsService)
    events_mock.insert_event = AsyncMock(return_value=None)
    events_service = cast(AgentEventsService, events_mock)
    handlers = AgentRunCallbackHandler.build_callbacks(run_id, events_service)
    config: dict[str, object] = {"callbacks": handlers}

    model = GenericFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "reasoning_content": "Debo llamar a get_server_status antes de resumir."
                    },
                    tool_calls=[
                        {
                            "name": "get_server_status",
                            "args": {"server": "server-x"},
                            "id": "call_server_status_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(
                    content=(
                        "Resumen de server-x: UP, CPU 38%, memoria 67%, sin alertas."
                    )
                ),
            ]
        )
    )

    tool = StructuredTool.from_function(
        coroutine=_get_server_status_tool_acoro,
        name="get_server_status",
        description="Devuelve JSON con estado del servidor.",
    )

    messages: list[HumanMessage | AIMessage | ToolMessage] = [
        HumanMessage(content="¿Estado de server-x?"),
    ]
    first_ai = await model.ainvoke(messages, config=config)
    messages.append(first_ai)
    assert len(first_ai.tool_calls) == 1
    tool_call = first_ai.tool_calls[0]
    # Entrada tipo ToolCall: ``tool_call_id`` va en el dict (evita duplicado en ``_prep_run_args``).
    tool_out = await tool.ainvoke(
        {
            "name": str(tool_call["name"]),
            "args": dict(tool_call["args"]),
            "id": str(tool_call["id"]),
            "type": "tool_call",
        },
        config=config,
    )
    messages.append(
        ToolMessage(
            content=tool_out if isinstance(tool_out, str) else str(tool_out),
            name=str(tool_call["name"]),
            tool_call_id=str(tool_call["id"]),
        )
    )
    second_ai = await model.ainvoke(messages, config=config)

    assert "server-x" in (second_ai.content or "")
    events_mock.insert_event.assert_awaited()
    event_types = [c.kwargs["event_type"] for c in events_mock.insert_event.await_args_list]
    assert event_types == [
        "llm_start",
        "llm_end",
        "tool_start",
        "tool_end",
        "llm_start",
        "llm_end",
    ]
    for call in events_mock.insert_event.await_args_list:
        assert call.kwargs["agent_run_id"] == run_id

    last_llm_end = events_mock.insert_event.await_args_list[-1].kwargs["payload"]
    assert "llm_response" in last_llm_end
    assert "UP" in str(last_llm_end["llm_response"])
