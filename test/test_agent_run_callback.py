"""Callbacks de tools: el log de fin y de error lleva el nombre y la duración reales."""

from __future__ import annotations

import logging
from uuid import uuid4

import pytest

from agent.interceptors.agent_run_callback import AgentRunCallbackHandler


def _handler() -> AgentRunCallbackHandler:
    return AgentRunCallbackHandler(agent_run_id=uuid4())


async def test_tool_end_logs_the_tool_name_and_a_real_duration(caplog: pytest.LogCaptureFixture) -> None:
    handler = _handler()
    run_id = uuid4()
    caplog.set_level(logging.INFO)

    await handler.on_tool_start({'name': 'mail_read_inbox'}, '{}', run_id=run_id)
    await handler.on_tool_end('ok', run_id=run_id)

    line = next(r.getMessage() for r in caplog.records if r.getMessage().startswith('tool_end'))
    assert 'tool=mail_read_inbox' in line
    assert 'tool=None' not in line


async def test_tool_error_logs_the_tool_name(caplog: pytest.LogCaptureFixture) -> None:
    handler = _handler()
    run_id = uuid4()
    caplog.set_level(logging.INFO)

    await handler.on_tool_start({'name': 'a2a_send_to_remote'}, '{}', run_id=run_id)
    await handler.on_tool_error(RuntimeError('boom'), run_id=run_id)

    line = next(r.getMessage() for r in caplog.records if r.getMessage().startswith('tool_error'))
    assert 'tool=a2a_send_to_remote' in line


async def test_two_tools_running_at_once_keep_their_own_names(caplog: pytest.LogCaptureFixture) -> None:
    handler = _handler()
    first, second = uuid4(), uuid4()
    caplog.set_level(logging.INFO)

    await handler.on_tool_start({'name': 'tool_a'}, '{}', run_id=first)
    await handler.on_tool_start({'name': 'tool_b'}, '{}', run_id=second)
    await handler.on_tool_end('ok', run_id=second)
    await handler.on_tool_end('ok', run_id=first)

    ends = [r.getMessage() for r in caplog.records if r.getMessage().startswith('tool_end')]
    assert 'tool=tool_b' in ends[0]
    assert 'tool=tool_a' in ends[1]
