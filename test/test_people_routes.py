"""``POST /people/verify``: protegido con clave compartida y con respuesta mínima."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from exception.mcp import MCPClientError
from http_api.routers import people_routes
from services.bmc import tool_handler
from type_defs.models.bmc.person import PersonCheck

KEY = 'clave-de-prueba'
EMAIL = 'nia.correo@henkia.com'


class FakeSettings:
    def __init__(self, verify_api_key: str) -> None:
        self.verify_api_key = verify_api_key


class FakeHandler:
    def __init__(self, verify_api_key: str = KEY) -> None:
        self.settings = FakeSettings(verify_api_key)
        self.client = object()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(tool_handler, 'get_shared_handler', FakeHandler)
    app = FastAPI()
    app.include_router(people_routes.router)
    return TestClient(app)


def _stub_check(monkeypatch: pytest.MonkeyPatch, check: PersonCheck | Exception) -> list[str]:
    seen: list[str] = []

    async def fake(_client: object, email: str) -> PersonCheck:
        seen.append(email)
        if isinstance(check, Exception):
            raise check
        return check

    monkeypatch.setattr(people_routes, 'verify_person_by_email', fake)
    return seen


def _post(client: TestClient, key: str | None = KEY, email: str = EMAIL) -> object:
    headers = {} if key is None else {'X-API-Key': key}
    return client.post('/people/verify', json={'email': email}, headers=headers)


def test_valid_key_returns_only_exists_and_enabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _stub_check(monkeypatch, PersonCheck(exists=True, enabled=True))

    response = _post(client)

    assert response.status_code == HTTPStatus.OK  # type: ignore[attr-defined]
    assert response.json() == {'exists': True, 'enabled': True}  # type: ignore[attr-defined]
    assert seen == [EMAIL]


def test_disabled_person_is_reported_as_such(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_check(monkeypatch, PersonCheck(exists=True, enabled=False))

    assert _post(client).json() == {'exists': True, 'enabled': False}  # type: ignore[attr-defined]


@pytest.mark.parametrize('key', [None, 'otra-clave', ''])
def test_missing_or_wrong_key_is_rejected_without_searching(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    seen = _stub_check(monkeypatch, PersonCheck(exists=True, enabled=True))

    response = _post(client, key)

    assert response.status_code == HTTPStatus.UNAUTHORIZED  # type: ignore[attr-defined]
    assert seen == []


def test_without_a_configured_key_the_endpoint_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool_handler, 'get_shared_handler', lambda: FakeHandler(verify_api_key=''))
    seen = _stub_check(monkeypatch, PersonCheck(exists=True, enabled=True))
    app = FastAPI()
    app.include_router(people_routes.router)

    response = _post(TestClient(app), key='')

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE  # type: ignore[attr-defined]
    assert seen == []


def test_bmc_failure_is_a_bad_gateway_without_leaking_the_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_check(monkeypatch, MCPClientError('token secreto caducado'))

    response = _post(client)

    assert response.status_code == HTTPStatus.BAD_GATEWAY  # type: ignore[attr-defined]
    assert 'secreto' not in response.text  # type: ignore[attr-defined]


@pytest.mark.parametrize('email', ['', '   '])
def test_empty_email_is_a_validation_error(client: TestClient, monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    _stub_check(monkeypatch, PersonCheck(exists=True, enabled=True))

    assert _post(client, email=email).status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # type: ignore[attr-defined]
