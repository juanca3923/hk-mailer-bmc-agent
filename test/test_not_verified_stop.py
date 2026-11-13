"""NotVerifiedStop: a not-verified person ends the run with the summary, without another model call."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from agent.middleware.not_verified_stop import NotVerifiedStop
from constants.bmc.messages import NOT_VERIFIED_MARKER, USER_ERROR_MESSAGE_PERSON_NOT_FOUND

CONFIG: dict[str, Any] = {'configurable': {'thread_id': 't1'}}
EMAIL = 'ghost@example.com'
TWO_MODEL_CALLS = 2


class ScriptedModel(GenericFakeChatModel):
    """Fake chat model that accepts ``bind_tools`` and counts its calls."""

    calls: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedModel:  # noqa: ARG002
        return self

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        return super()._generate(*args, **kwargs)


def _graph(tool_message: str) -> tuple[Any, ScriptedModel]:
    @tool
    def bmc_create_incident() -> str:
        """Create."""
        return tool_message

    call = AIMessage(content='', tool_calls=[{'name': 'bmc_create_incident', 'args': {}, 'id': 'c1'}])
    messages: Iterator[AIMessage] = iter([call, AIMessage('respuesta del modelo')])
    model = ScriptedModel(messages=messages)
    return create_agent(model, [bmc_create_incident], middleware=[NotVerifiedStop()]), model


def _failure(message: str) -> str:
    return json.dumps({'success': False, 'message': message}, ensure_ascii=False)


def test_person_not_found_message_carries_marker_email_and_no_retry() -> None:
    message = USER_ERROR_MESSAGE_PERSON_NOT_FOUND.format(email=EMAIL)

    assert NOT_VERIFIED_MARKER == 'Estado final: No verificado'
    assert message.startswith(NOT_VERIFIED_MARKER)
    assert EMAIL in message
    assert 'no reintentes' in message
    assert 'Error' not in message


async def test_not_verified_ends_the_run_with_the_summary_and_no_more_model_calls() -> None:
    message = USER_ERROR_MESSAGE_PERSON_NOT_FOUND.format(email=EMAIL)
    graph, model = _graph(_failure(message))

    result = await graph.ainvoke({'messages': [HumanMessage('crea ticket')]}, config=CONFIG)

    last = result['messages'][-1]
    assert isinstance(last, AIMessage)
    assert model.calls == 1
    assert 'respuesta del modelo' not in str(last.content)
    assert 'Ticket creado: —' in last.content
    assert f'Solicitante: {EMAIL}' in last.content
    assert message in last.content
    assert 'success' not in last.content


def test_sync_path_also_ends_the_run() -> None:
    message = USER_ERROR_MESSAGE_PERSON_NOT_FOUND.format(email=EMAIL)
    graph, model = _graph(_failure(message))

    result = graph.invoke({'messages': [HumanMessage('crea ticket')]}, config=CONFIG)

    assert model.calls == 1
    assert NOT_VERIFIED_MARKER in result['messages'][-1].content


async def test_a_different_failure_does_not_trigger_the_stop() -> None:
    graph, model = _graph(_failure('Error: Permiso denegado en BMC para esta operación.'))

    result = await graph.ainvoke({'messages': [HumanMessage('crea ticket')]}, config=CONFIG)

    assert model.calls == TWO_MODEL_CALLS
    assert result['messages'][-1].content == 'respuesta del modelo'


async def test_without_marker_it_does_not_intervene() -> None:
    graph, model = _graph(json.dumps({'success': True, 'message': 'INC000001'}))

    result = await graph.ainvoke({'messages': [HumanMessage('crea ticket')]}, config=CONFIG)

    assert model.calls == TWO_MODEL_CALLS
    assert result['messages'][-1].content == 'respuesta del modelo'
