"""Topes por run: el agente no puede repetir tools ni llamadas al modelo sin fin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from agent.middleware.run_limits import build_run_limit_middleware

CONFIG: dict[str, Any] = {'configurable': {'thread_id': 't1'}}
TOOL_LIMIT = 3
TOTAL_TOOL_LIMIT = 4
MODEL_LIMIT = 5
MANY_CALLS = 12


class ScriptedModel(GenericFakeChatModel):
    """Fake chat model that accepts ``bind_tools`` and counts its calls."""

    calls: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedModel:  # noqa: ARG002
        return self

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        return super()._generate(*args, **kwargs)


def _call(tool_name: str, idx: int) -> AIMessage:
    return AIMessage(content='', tool_calls=[{'name': tool_name, 'args': {}, 'id': f'c{idx}'}])


def _model(tool_name: str, times: int) -> ScriptedModel:
    messages: Iterator[AIMessage] = iter([*[_call(tool_name, i) for i in range(times)], AIMessage('listo')])
    return ScriptedModel(messages=messages)


def _graph(model: ScriptedModel, executed: list[str], **limits: Any) -> Any:
    @tool
    def a2a_send_to_remote() -> str:
        """Delegate."""
        executed.append('a2a')
        return 'sin ticket'

    @tool
    def other_tool() -> str:
        """Other."""
        executed.append('other')
        return 'ok'

    middleware = build_run_limit_middleware(**limits)
    return create_agent(model, [a2a_send_to_remote, other_tool], middleware=middleware)


def _tool_messages(result: dict[str, Any]) -> list[ToolMessage]:
    return [m for m in result['messages'] if isinstance(m, ToolMessage)]


async def test_a_tool_stops_executing_after_its_own_limit() -> None:
    executed: list[str] = []
    graph = _graph(
        _model('a2a_send_to_remote', 6),
        executed,
        max_model_calls=0,
        max_tool_calls=0,
        per_tool={'a2a_send_to_remote': TOOL_LIMIT},
    )

    result = await graph.ainvoke({'messages': [HumanMessage('hola')]}, config=CONFIG)

    assert executed.count('a2a') == TOOL_LIMIT
    assert any('Do not call' in str(m.content) for m in _tool_messages(result))


async def test_the_total_tool_limit_blocks_further_calls_of_any_tool() -> None:
    executed: list[str] = []
    graph = _graph(_model('other_tool', 8), executed, max_model_calls=0, max_tool_calls=TOTAL_TOOL_LIMIT, per_tool={})

    result = await graph.ainvoke({'messages': [HumanMessage('hola')]}, config=CONFIG)

    assert len(executed) == TOTAL_TOOL_LIMIT
    assert result['messages'][-1].content == 'listo'


async def test_the_model_limit_ends_the_run_with_an_error() -> None:
    executed: list[str] = []
    model = _model('other_tool', 30)
    graph = _graph(model, executed, max_model_calls=MODEL_LIMIT, max_tool_calls=0, per_tool={})

    with pytest.raises(ModelCallLimitExceededError):
        await graph.ainvoke({'messages': [HumanMessage('hola')]}, config=CONFIG)

    assert model.calls <= MODEL_LIMIT


async def test_a_limit_of_zero_disables_it() -> None:
    executed: list[str] = []
    graph = _graph(
        _model('other_tool', MANY_CALLS), executed, max_model_calls=0, max_tool_calls=0, per_tool={'other_tool': 0}
    )

    await graph.ainvoke({'messages': [HumanMessage('hola')]}, config=CONFIG)

    assert len(executed) == MANY_CALLS


def test_no_limits_means_no_middleware() -> None:
    assert build_run_limit_middleware(max_model_calls=0, max_tool_calls=0, per_tool={}) == []
