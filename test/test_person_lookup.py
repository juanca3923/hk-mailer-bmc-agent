"""Unit tests for CTM:People reporter-identity resolution and its tie-break rule."""

from __future__ import annotations

from constants.bmc.fields import AR_FIELD_PEOPLE_FIRST_NAME, AR_FIELD_PEOPLE_LAST_NAME, AR_FIELD_PEOPLE_LOGIN_ID
from exception.mcp import MCPClientError
from services.bmc.person_lookup import resolve_reporter_identity
from type_defs.models.bmc.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues
from type_defs.models.bmc.outputs import BaseOutput
from type_defs.models.bmc.person import ReporterIdentity

EMAIL = 'juan.londonog@henkia.com'


def _entry(login_id: str, first_name: str, last_name: str) -> BmcEntry:
    return BmcEntry(
        values=BmcEntryValues(
            data={
                AR_FIELD_PEOPLE_LOGIN_ID: login_id,
                AR_FIELD_PEOPLE_FIRST_NAME: first_name,
                AR_FIELD_PEOPLE_LAST_NAME: last_name,
            },
        ),
    )


class FakeClient:
    """Minimal stand-in for ``BmcClient`` exposing only ``search_person_by_email``."""

    def __init__(self, entries: list[BmcEntry] | None = None, error: MCPClientError | None = None) -> None:
        self._entries = entries or []
        self._error = error

    async def search_person_by_email(self, email: str) -> BmcEntryListResponse:  # noqa: ARG002
        if self._error is not None:
            raise self._error
        return BmcEntryListResponse(entries=self._entries)


async def test_resolves_single_match() -> None:
    client = FakeClient([_entry('AgentesIA', 'Agentes', 'IA')])

    result = await resolve_reporter_identity(client, EMAIL)

    assert result == ReporterIdentity(first_name='Agentes', last_name='IA')


async def test_prefers_email_shaped_login_id_over_bot_style_id() -> None:
    """Regression for the exact ambiguity BMC returned in practice: a bot People
    record (``AgentesIA``, no ``@``) sharing an email with a real person's record
    (``juan.londonog@arus.com.co``, looks like an email)."""
    client = FakeClient(
        [
            _entry('AgentesIA', 'Agentes', 'IA'),
            _entry('juan.londonog@arus.com.co', 'Juan Camilo', 'Londono Graciano'),
        ],
    )

    result = await resolve_reporter_identity(client, EMAIL)

    assert result == ReporterIdentity(first_name='Juan Camilo', last_name='Londono Graciano')


async def test_falls_back_to_first_entry_when_no_login_id_looks_like_email() -> None:
    client = FakeClient([_entry('AgentesIA', 'Agentes', 'IA'), _entry('BotSecundario', 'Bot', 'Secundario')])

    result = await resolve_reporter_identity(client, EMAIL)

    assert result == ReporterIdentity(first_name='Agentes', last_name='IA')


async def test_falls_back_to_first_entry_when_several_login_ids_look_like_email() -> None:
    client = FakeClient(
        [
            _entry('primero@arus.com.co', 'Primero', 'Persona'),
            _entry('segundo@arus.com.co', 'Segundo', 'Persona'),
        ],
    )

    result = await resolve_reporter_identity(client, EMAIL)

    assert result == ReporterIdentity(first_name='Primero', last_name='Persona')


async def test_returns_error_when_no_entries_found() -> None:
    client = FakeClient([])

    result = await resolve_reporter_identity(client, EMAIL)

    assert isinstance(result, BaseOutput)
    assert result.success is False
    assert EMAIL in result.message


async def test_returns_error_when_matched_entry_has_incomplete_name() -> None:
    client = FakeClient([_entry('juan.londonog@arus.com.co', '', 'Londono Graciano')])

    result = await resolve_reporter_identity(client, EMAIL)

    assert isinstance(result, BaseOutput)
    assert result.success is False


async def test_returns_error_when_lookup_fails() -> None:
    client = FakeClient(error=MCPClientError('Error: BMC no responde.'))

    result = await resolve_reporter_identity(client, EMAIL)

    assert isinstance(result, BaseOutput)
    assert result.success is False
    assert result.message == 'Error: BMC no responde.'


async def test_strips_whitespace_before_querying() -> None:
    seen_emails: list[str] = []

    class RecordingClient(FakeClient):
        async def search_person_by_email(self, email: str) -> BmcEntryListResponse:
            seen_emails.append(email)
            return await super().search_person_by_email(email)

    client = RecordingClient([_entry('juan.londonog@arus.com.co', 'Juan', 'Londono')])

    await resolve_reporter_identity(client, f'  {EMAIL}  ')

    assert seen_emails == [EMAIL]
