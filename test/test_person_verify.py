"""``verify_person_by_email``: la persona existe en CTM:People y está habilitada."""

from __future__ import annotations

import pytest

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.constants import AR_FIELD_PEOPLE_LOGIN_ID, AR_FIELD_PEOPLE_STATUS
from bmc.libs.helpers.person_lookup import PersonCheck, verify_person_by_email
from bmc.type_defs.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues

EMAIL = 'nia.correo@henkia.com'


def _entry(login_id: str, status: str | None) -> BmcEntry:
    data: dict[str, str] = {AR_FIELD_PEOPLE_LOGIN_ID: login_id}
    if status is not None:
        data[AR_FIELD_PEOPLE_STATUS] = status
    return BmcEntry(values=BmcEntryValues(data=data))


class FakeClient:
    def __init__(self, entries: list[BmcEntry] | None = None, error: MCPClientError | None = None) -> None:
        self.entries = entries or []
        self.error = error
        self.emails: list[str] = []

    async def search_person_by_email(self, email: str) -> BmcEntryListResponse:
        self.emails.append(email)
        if self.error is not None:
            raise self.error
        return BmcEntryListResponse(entries=self.entries)


async def test_enabled_person_is_valid() -> None:
    client = FakeClient([_entry('nia.correo', 'Enabled')])

    assert await verify_person_by_email(client, EMAIL) == PersonCheck(exists=True, enabled=True)


@pytest.mark.parametrize('status', ['Offline', 'Obsolete', '', None])
async def test_person_that_is_not_enabled_exists_but_is_not_enabled(status: str | None) -> None:
    client = FakeClient([_entry('nia.correo', status)])

    assert await verify_person_by_email(client, EMAIL) == PersonCheck(exists=True, enabled=False)


async def test_status_comparison_ignores_case_and_spaces() -> None:
    client = FakeClient([_entry('nia.correo', '  enabled ')])

    assert (await verify_person_by_email(client, EMAIL)).enabled is True


async def test_unknown_email_does_not_exist() -> None:
    assert await verify_person_by_email(FakeClient([]), EMAIL) == PersonCheck(exists=False, enabled=False)


async def test_the_email_is_trimmed_before_searching() -> None:
    client = FakeClient([_entry('nia.correo', 'Enabled')])

    await verify_person_by_email(client, f'  {EMAIL}  ')

    assert client.emails == [EMAIL]


async def test_a_bot_record_sharing_the_email_does_not_decide_the_result() -> None:
    """Misma regla de desempate que ``resolve_reporter_identity``: gana el login con forma de correo."""
    client = FakeClient([_entry('AgentesIA', 'Enabled'), _entry('nia@henkia.com', 'Offline')])

    assert await verify_person_by_email(client, EMAIL) == PersonCheck(exists=True, enabled=False)


async def test_lookup_errors_are_not_reported_as_a_missing_person() -> None:
    client = FakeClient(error=MCPClientError('BMC caído'))

    with pytest.raises(MCPClientError):
        await verify_person_by_email(client, EMAIL)


async def test_people_search_also_asks_bmc_for_the_status_field() -> None:
    from types import SimpleNamespace  # noqa: PLC0415

    from bmc.libs.api_client import BmcClient  # noqa: PLC0415

    seen: dict[str, str] = {}

    class CapturingClient(BmcClient):
        async def get_json(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, list[object]]:  # type: ignore[override]
            seen.update(params or {})
            return {'entries': []}

    client = CapturingClient(settings=SimpleNamespace(form_people_query='CTM:People'), connection_manager=object())  # type: ignore[arg-type]

    await client.search_person_by_email(EMAIL)

    assert AR_FIELD_PEOPLE_STATUS in seen['fields']
