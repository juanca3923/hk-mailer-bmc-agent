"""Tests for the tool base class and the visible-errors policy."""

from __future__ import annotations

from typing import Annotated

import pytest
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field

from agent.internal_tools.base import ToolSet
from agent.tool_error_policy import configure_tool_error_handling, format_validation_error
from exception import ToolAgentError

MAX_MESSAGE_CHARS = 300


class Payload(BaseModel):
    secret_value: int


def _call(name: str, args: dict[str, object]) -> dict[str, object]:
    return {'name': name, 'args': args, 'id': 'call-1', 'type': 'tool_call'}


async def _echo(text: Annotated[str, Field(description='Text to echo.')], config: RunnableConfig) -> str:
    return f'{text}:{(config.get("configurable") or {}).get("k")}'


async def _agent_error() -> str:
    raise ToolAgentError('mensaje del dominio')


async def _validation_in_body() -> str:
    Payload(secret_value='tarjeta-1234')  # type: ignore[arg-type]
    return 'ok'


async def _unexpected() -> str:
    raise RuntimeError('boom con detalle')


def _tool(coroutine: object, name: str) -> StructuredTool:
    tool = ToolSet.build(coroutine, name=name, description=f'{name} description.')  # type: ignore[arg-type]
    configure_tool_error_handling([tool])
    return tool


def test_description_is_required() -> None:
    with pytest.raises(ValueError, match='description'):
        ToolSet.build(_agent_error, name='x', description=' ')


def test_schema_keeps_the_signature_and_field_descriptions() -> None:
    tool = ToolSet.build(_echo, name='echo', description='Echo.')

    schema = tool.args_schema.model_json_schema()  # type: ignore[union-attr]
    assert list(schema['properties']) == ['text']
    assert schema['properties']['text']['description'] == 'Text to echo.'


@pytest.mark.asyncio
async def test_runnable_config_is_still_injected() -> None:
    tool = _tool(_echo, 'echo')

    out = await tool.ainvoke(_call('echo', {'text': 'hi'}), config={'configurable': {'k': 'v'}})

    assert out.content == 'hi:v'


@pytest.mark.asyncio
async def test_domain_errors_reach_the_llm_unchanged() -> None:
    out = await _tool(_agent_error, 'agent_error').ainvoke(_call('agent_error', {}))

    assert out.content == 'mensaje del dominio'
    assert out.status == 'error'


@pytest.mark.asyncio
async def test_validation_error_in_the_body_names_the_field_but_not_the_value() -> None:
    out = await _tool(_validation_in_body, 'validation').ainvoke(_call('validation', {}))

    assert 'secret_value' in out.content
    assert 'tarjeta-1234' not in out.content
    assert out.status == 'error'


@pytest.mark.asyncio
async def test_invalid_arguments_name_the_field() -> None:
    out = await _tool(_echo, 'echo').ainvoke(_call('echo', {}))

    assert 'text' in out.content
    assert out.content != 'Tool input validation error'


@pytest.mark.asyncio
async def test_unexpected_errors_become_a_short_message_with_the_type() -> None:
    out = await _tool(_unexpected, 'unexpected').ainvoke(_call('unexpected', {}))

    assert out.status == 'error'
    assert 'unexpected' in out.content
    assert 'RuntimeError' in out.content
    assert 'boom con detalle' in out.content


@pytest.mark.asyncio
async def test_unexpected_error_message_is_trimmed() -> None:
    async def long_error() -> str:
        raise RuntimeError('x' * 1000)

    out = await _tool(long_error, 'long_error').ainvoke(_call('long_error', {}))

    assert len(out.content) < MAX_MESSAGE_CHARS


def test_sync_tools_are_guarded_too() -> None:
    def sync_boom() -> str:
        raise RuntimeError('sync boom')

    tool = ToolSet.build(sync_boom, name='sync_boom', description='Sync.')
    configure_tool_error_handling([tool])

    out = tool.invoke(_call('sync_boom', {}))

    assert 'RuntimeError' in out.content


def test_format_validation_error_lists_fields_without_input() -> None:
    try:
        Payload(secret_value='zzz')  # type: ignore[arg-type]
    except ValueError as exc:
        text = format_validation_error(exc)  # type: ignore[arg-type]
    assert 'secret_value' in text
    assert 'zzz' not in text


def test_tool_exception_is_not_wrapped() -> None:
    assert issubclass(ToolAgentError, ToolException)
