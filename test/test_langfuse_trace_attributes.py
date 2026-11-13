"""Atributos de trace de Langfuse: nombre, sesión, tags y metadata por run."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from agent.observability import langfuse_tracing
from agent.observability.langfuse_tracing import build_trace_attributes, trace_attributes
from agent.runtime import runner as runner_module
from agent.runtime.runner import AgentRunner
from type_defs.models.agent.agent_turn import AgentTurnResult, TurnContext

MAX_CHARS = 200


def test_the_session_is_the_chat_and_the_name_and_tags_say_agent_and_mode() -> None:
    chat_id, run_id = uuid4(), uuid4()

    attributes = build_trace_attributes(agent_slug='agent_bmc', chat_id=chat_id, run_id=run_id, mode='chat')

    assert attributes['session_id'] == str(chat_id)
    assert attributes['trace_name'] == 'agent_bmc:chat'
    assert attributes['tags'] == ['agent_bmc', 'chat']
    assert attributes['metadata'] == {'agent_run_id': str(run_id), 'own_chat_id': str(chat_id)}


def test_a_caller_session_replaces_the_own_chat_as_session_and_is_kept_in_the_metadata() -> None:
    chat_id, run_id = uuid4(), uuid4()
    caller = {'caller_agent': 'agent_bmc', 'caller_chat_id': 'chat-del-mailer', 'caller_run_id': 'run-del-mailer'}

    attributes = build_trace_attributes(
        agent_slug='agent_bmc', chat_id=chat_id, run_id=run_id, mode='a2a', caller=caller
    )

    assert attributes['session_id'] == 'chat-del-mailer'
    assert attributes['metadata']['caller_run_id'] == 'run-del-mailer'
    assert attributes['metadata']['own_chat_id'] == str(chat_id)


def test_values_are_ascii_and_at_most_200_characters() -> None:
    caller = {'caller_chat_id': 'ñ' * 300 + 'abc', 'caller_run_id': 'x' * 500, 'caller_agent': 'mañana'}

    attributes = build_trace_attributes(
        agent_slug='agent_bmc', chat_id=uuid4(), run_id=uuid4(), mode='a2a', caller=caller
    )

    for value in [attributes['session_id'], *attributes['metadata'].values()]:
        assert value.isascii()
        assert len(value) <= MAX_CHARS


def test_without_langfuse_credentials_there_is_no_tracing_context() -> None:
    settings = SimpleNamespace(langfuse_tracing_ready=False, agent_slug='agent_bmc')

    context = trace_attributes(settings=settings, chat_id=uuid4(), run_id=uuid4(), mode='chat')  # type: ignore[arg-type]

    assert isinstance(context, type(nullcontext()))


def test_with_langfuse_credentials_the_attributes_are_propagated(monkeypatch: Any) -> None:
    received: dict[str, Any] = {}

    def fake_propagate(**kwargs: Any) -> AbstractContextManager[None]:
        received.update(kwargs)
        return nullcontext()

    monkeypatch.setattr(langfuse_tracing, 'propagate_attributes', fake_propagate)
    settings = SimpleNamespace(langfuse_tracing_ready=True, agent_slug='agent_bmc')
    chat_id = uuid4()

    trace_attributes(settings=settings, chat_id=chat_id, run_id=uuid4(), mode='awake')  # type: ignore[arg-type]

    assert received['session_id'] == str(chat_id)
    assert received['trace_name'] == 'agent_bmc:awake'


class _FakeGraph:
    """Graph stub that records whether it ran inside the trace context."""

    def __init__(self, state: dict[str, bool]) -> None:
        self._state = state

    async def ainvoke(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self._state['inside'] = self._state['entered'] and not self._state['exited']
        return {'messages': [AIMessage('listo')]}


async def _run(monkeypatch: Any, **turn_kwargs: Any) -> tuple[dict[str, bool], dict[str, Any]]:
    state = {'entered': False, 'exited': False, 'inside': False}
    seen: dict[str, Any] = {}
    ctx = TurnContext(chat_id=uuid4(), run_id=uuid4(), messages=[HumanMessage('hola')])

    @contextmanager
    def fake_trace_attributes(**kwargs: Any) -> Iterator[None]:
        seen.update(kwargs)
        state['entered'] = True
        yield
        state['exited'] = True

    async def fake_prepare(**_kwargs: Any) -> TurnContext:
        return ctx

    async def fake_finish(**_kwargs: Any) -> AgentTurnResult:
        return AgentTurnResult(reply='listo', chat_id=ctx.chat_id, run_id=ctx.run_id, status='success')

    monkeypatch.setattr(runner_module, 'trace_attributes', fake_trace_attributes)
    monkeypatch.setattr(AgentRunner, 'prepare_turn', staticmethod(fake_prepare))
    monkeypatch.setattr(AgentRunner, 'finish_turn_success', staticmethod(fake_finish))
    monkeypatch.setattr(AgentRunner, 'build_graph_invoke_config', staticmethod(lambda *_a, **_k: {}))
    fake_settings = SimpleNamespace(agent_slug='agent_bmc')
    monkeypatch.setattr(runner_module.Settings, 'load', staticmethod(lambda: fake_settings))

    await AgentRunner().run_agent_turn(user_message='hola', graph=_FakeGraph(state), **turn_kwargs)
    return state, seen


async def test_the_graph_runs_inside_the_trace_context_in_chat_mode(monkeypatch: Any) -> None:
    state, seen = await _run(monkeypatch)

    assert state['inside'] is True
    assert seen['mode'] == 'chat'
    assert seen['caller'] is None


async def test_a2a_turns_are_traced_as_a2a_with_the_caller(monkeypatch: Any) -> None:
    caller = {'caller_agent': 'mailer_agent', 'caller_chat_id': 'chat-1', 'caller_run_id': 'run-1'}

    _state, seen = await _run(monkeypatch, origin='a2a', caller=caller)

    assert seen['mode'] == 'a2a'
    assert seen['caller'] == caller
