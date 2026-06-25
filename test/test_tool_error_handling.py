"""Tests for global tool error policy (handle_tool_error → ToolMessage content)."""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool, ToolException

from agent.tool_error_policy import configure_tool_error_handling
from exception import ToolAgentError

_TOOL_ERROR_MSG = 'Operación no permitida: permisos insuficientes.'


class ExampleToolAgentError(ToolAgentError):
    """Example domain tool error for tests."""


async def _raise_example_tool_error() -> str:
    """Simulates an internal tool failing with a user-facing message."""
    raise ExampleToolAgentError(_TOOL_ERROR_MSG)


def test_tool_agent_error_is_tool_exception() -> None:
    """ToolAgentError is a ToolException for LangChain tool error handling."""
    exc = ExampleToolAgentError(_TOOL_ERROR_MSG)
    assert isinstance(exc, ToolException)
    assert isinstance(exc, ToolAgentError)
    assert str(exc) == _TOOL_ERROR_MSG


@pytest.mark.asyncio
async def test_handle_tool_error_returns_exception_message() -> None:
    """Raised ToolAgentError becomes tool output text for the LLM."""
    tool = StructuredTool.from_function(
        coroutine=_raise_example_tool_error,
        name='example_failing_tool',
        description='Example tool that fails (test stub).',
    )
    configure_tool_error_handling([tool])

    out = await tool.ainvoke(
        {
            'name': 'example_failing_tool',
            'args': {},
            'id': 'call_example_1',
            'type': 'tool_call',
        }
    )
    content = out if isinstance(out, str) else str(out)
    assert _TOOL_ERROR_MSG in content


@pytest.mark.asyncio
async def test_tool_error_history_allows_second_llm_invoke() -> None:
    """AIMessage + tool_use + tool_result does not break a follow-up model call."""
    tool = StructuredTool.from_function(
        coroutine=_raise_example_tool_error,
        name='example_failing_tool',
        description='Example tool that fails (test stub).',
    )
    configure_tool_error_handling([tool])

    model = GenericFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content='',
                    tool_calls=[
                        {
                            'name': 'example_failing_tool',
                            'args': {},
                            'id': 'call_example_1',
                            'type': 'tool_call',
                        }
                    ],
                ),
                AIMessage(
                    content='No pude completar la operación: faltan permisos.'
                ),
            ]
        )
    )

    messages: list[HumanMessage | AIMessage | ToolMessage] = [
        HumanMessage(content='Ejecuta la operación de ejemplo.'),
    ]
    first_ai = await model.ainvoke(messages)
    messages.append(first_ai)
    assert len(first_ai.tool_calls) == 1
    tool_call = first_ai.tool_calls[0]

    tool_out = await tool.ainvoke(
        {
            'name': str(tool_call['name']),
            'args': dict(tool_call['args']),
            'id': str(tool_call['id']),
            'type': 'tool_call',
        }
    )
    tool_content = tool_out if isinstance(tool_out, str) else str(tool_out)
    assert _TOOL_ERROR_MSG in tool_content

    messages.append(
        ToolMessage(
            content=tool_content,
            name=str(tool_call['name']),
            tool_call_id=str(tool_call['id']),
        )
    )
    second_ai = await model.ainvoke(messages)
    assert isinstance(second_ai.content, str)
    assert 'permisos' in second_ai.content.lower()
