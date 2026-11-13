"""Autochequeo de arranque del BMC: avisa si el campo de estado de CTM:People no existe en la instancia."""

from __future__ import annotations

import asyncio

import pytest

from constants.bmc import AR_FIELD_PEOPLE_STATUS
from exception.mcp import MCPClientError
from services.startup import preflight
from services.startup.preflight import check_people_status_field, run_startup_preflight
from type_defs.models.bmc.ar_api import BmcEntryListResponse


class FakeClient:
    def __init__(self, error: MCPClientError | None = None) -> None:
        self.error = error
        self.emails: list[str] = []

    async def search_person_by_email(self, email: str) -> BmcEntryListResponse:
        self.emails.append(email)
        if self.error is not None:
            raise self.error
        return BmcEntryListResponse(entries=[])


async def test_a_clean_answer_means_the_status_field_exists(caplog: pytest.LogCaptureFixture) -> None:
    client = FakeClient()

    with caplog.at_level('INFO'):
        ok = await check_people_status_field(client)  # type: ignore[arg-type]

    assert ok is True
    assert 'WARNING' not in caplog.text
    assert client.emails[0].endswith('.invalid')  # dirección ficticia: no busca a una persona real


async def test_a_rejected_request_points_at_the_status_field_name(caplog: pytest.LogCaptureFixture) -> None:
    client = FakeClient(MCPClientError('Campo desconocido', status_code=400))

    with caplog.at_level('WARNING'):
        ok = await check_people_status_field(client)  # type: ignore[arg-type]

    assert ok is False
    assert AR_FIELD_PEOPLE_STATUS in caplog.text
    assert 'AR_FIELD_PEOPLE_STATUS' in caplog.text
    assert 'sin leer' not in caplog.text


@pytest.mark.parametrize('status_code', [401, 500, 503, None])
async def test_other_failures_do_not_blame_the_field_name(
    caplog: pytest.LogCaptureFixture, status_code: int | None
) -> None:
    client = FakeClient(MCPClientError('BMC no responde', status_code=status_code))

    with caplog.at_level('WARNING'):
        ok = await check_people_status_field(client)  # type: ignore[arg-type]

    assert ok is False
    assert 'BMC no responde' in caplog.text
    assert 'AR_FIELD_PEOPLE_STATUS' not in caplog.text


async def test_the_startup_wrapper_never_raises_when_the_client_cannot_be_built(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken() -> object:
        raise ValueError('BMC_BASE_URL no definida')

    monkeypatch.setattr(preflight, 'build_people_client', broken)

    with caplog.at_level('WARNING'):
        await run_startup_preflight()

    assert 'BMC_BASE_URL' in caplog.text


async def test_the_startup_wrapper_gives_up_when_bmc_hangs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Hanging:
        async def search_person_by_email(self, _email: str) -> None:
            await asyncio.sleep(10)

    monkeypatch.setattr(preflight, 'build_people_client', Hanging)
    monkeypatch.setattr(preflight, 'PREFLIGHT_TIMEOUT_SEC', 0.05)

    with caplog.at_level('WARNING'):
        await run_startup_preflight()

    assert 'tardó' in caplog.text or 'tardaron' in caplog.text
