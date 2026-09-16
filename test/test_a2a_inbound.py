"""Tests del endpoint A2A inbound (JSON-RPC) con grafo y runner mockeados."""

from __future__ import annotations

import uuid
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from http_api.a2a import router as a2a_router
from http_api.state import agent_state
from type_defs.dicts.agent_turn import AgentTurnResult


@pytest.fixture(autouse=True)
def _agent_state_up() -> None:
    """Línea base determinística para cada test; no representa el default de producción
    (``HTTP_ALLOW_CONCURRENT_TURNS=1``) — cada test deja explícita la política que necesita."""
    agent_state.clear_shutdown_requested()
    agent_state.set_status("UP")
    agent_state.set_allow_concurrent_turns(False)


@pytest.fixture(autouse=True)
def _a2a_tests_match_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los POST usan ``/a2a/agent_forge``; alinear con ``Settings`` y ``load_dotenv``.

    Si borramos ``A2A_ASSISTANT_ID``, ``load_dotenv(override=False)`` puede volver a
    rellenarlo desde ``.env``; una cadena vacía bloquea esa inyección y fuerza el slug.
    """
    monkeypatch.setenv("AGENT_SLUG", "agent_forge")
    monkeypatch.setenv("A2A_ASSISTANT_ID", "")


@pytest.fixture()
def a2a_only_app() -> FastAPI:
    """App mínima con solo el router A2A (sin lifespan de producción)."""
    app = FastAPI()
    app.state.graph = object()
    app.include_router(a2a_router)
    return app


def _runner_mock(chat_id: uuid.UUID, run_id: uuid.UUID) -> MagicMock:
    result = AgentTurnResult(reply="pong-a2a", chat_id=chat_id, run_id=run_id, status="success")
    runner = MagicMock()
    runner.run_agent_turn = AsyncMock(return_value=result)
    return runner


def test_message_send_ok(a2a_only_app: FastAPI) -> None:
    cid = uuid.uuid4()
    rid = uuid.uuid4()
    runner = _runner_mock(cid, rid)
    with patch("http_api.a2a.get_agent_runner", return_value=runner):
        with patch("http_api.a2a.get_agent_events_service", return_value=MagicMock()):
            client = TestClient(a2a_only_app)
            body = {
                "jsonrpc": "2.0",
                "id": "r1",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "hola"}],
                        "messageId": str(uuid.uuid4()),
                    },
                },
            }
            r = client.post("/a2a/agent_forge", json=body)
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["jsonrpc"] == "2.0"
    assert data.get("result")
    res = data["result"]
    assert res["contextId"] == str(cid)
    assert res["id"] == str(rid)
    arts = res.get("artifacts", [])
    assert arts and arts[0]["parts"][0]["text"] == "pong-a2a"


def test_message_send_unknown_method(a2a_only_app: FastAPI) -> None:
    with patch("http_api.a2a.get_agent_runner", return_value=MagicMock()):
        with patch("http_api.a2a.get_agent_events_service", return_value=MagicMock()):
            client = TestClient(a2a_only_app)
            r = client.post(
                "/a2a/agent_forge",
                json={"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {}},
            )
    assert r.status_code == HTTPStatus.OK
    assert "error" in r.json()


def test_message_send_busy_when_concurrent_turns_disabled(a2a_only_app: FastAPI) -> None:
    """Con HTTP_ALLOW_CONCURRENT_TURNS=0 (default del fixture): un run por turno."""
    agent_state.try_begin_task()  # simula un turno ya en curso
    try:
        with patch("http_api.a2a.get_agent_runner", return_value=MagicMock()):
            with patch("http_api.a2a.get_agent_events_service", return_value=MagicMock()):
                client = TestClient(a2a_only_app)
                body = {
                    "jsonrpc": "2.0",
                    "id": "x",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "hola"}],
                            "messageId": str(uuid.uuid4()),
                        },
                    },
                }
                r = client.post("/a2a/agent_forge", json=body)
        assert r.status_code == HTTPStatus.CONFLICT
    finally:
        agent_state.end_task()


def test_message_send_allowed_while_busy_when_concurrent_turns_enabled(a2a_only_app: FastAPI) -> None:
    """Con HTTP_ALLOW_CONCURRENT_TURNS=1: un turno nuevo no se rechaza aunque el agente ya
    esté DOING_TASK por otro turno en curso (solo se registra el conteo)."""
    agent_state.set_allow_concurrent_turns(True)
    agent_state.try_begin_task()  # simula un turno concurrente ya en curso
    try:
        cid = uuid.uuid4()
        rid = uuid.uuid4()
        runner = _runner_mock(cid, rid)
        with patch("http_api.a2a.get_agent_runner", return_value=runner):
            with patch("http_api.a2a.get_agent_events_service", return_value=MagicMock()):
                client = TestClient(a2a_only_app)
                body = {
                    "jsonrpc": "2.0",
                    "id": "x",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "hola"}],
                            "messageId": str(uuid.uuid4()),
                        },
                    },
                }
                r = client.post("/a2a/agent_forge", json=body)
        assert r.status_code == HTTPStatus.OK
        assert r.json().get("result")
        # El turno simulado al inicio sigue "en curso": el estado no debe volver a UP todavía.
        assert agent_state.status == "DOING_TASK"
    finally:
        agent_state.end_task()


def test_no_graph_503(a2a_only_app: FastAPI) -> None:
    a2a_only_app.state.graph = None
    client = TestClient(a2a_only_app)
    body = {
        "jsonrpc": "2.0",
        "id": "z",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "hola"}],
                "messageId": str(uuid.uuid4()),
            },
        },
    }
    r = client.post("/a2a/agent_forge", json=body)
    assert r.status_code == HTTPStatus.SERVICE_UNAVAILABLE
