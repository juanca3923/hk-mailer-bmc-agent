"""``bmc_attach_staged_files``: integración tool → operaciones reales de Incident / Work Order."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.internal_tools import bmc_tools
from agent.internal_tools.bmc_staged_files_tools import bmc_attach_staged_files
from constants.bmc import AR_FIELD_REQUEST_ID, AR_FIELD_STATUS, AR_FIELD_SUBMITTER
from services.bmc import tool_handler
from services.bmc.tool_handler import BaseToolHandler
from type_defs.models.bmc.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues

STAGING_ID = '0b9f2c1e-7a54-4c1d-9d0e-3f6a1b2c4d5e'
MAX_BYTES = 2048
TWO_FILES = 2
FILE_PLUS_NOTE = 2


class FakeSettings:
    """Stand-in for ``BmcSettings`` with what guards and attachments read."""

    def __init__(self, base: Path | None, allow_write: bool = True) -> None:
        self.username = 'svc_mosaico'
        self.assignee_display_name = 'Mosaico WebServices'
        self.attachment_base_dir = base
        self.max_attachment_bytes = MAX_BYTES
        self.allow_write = allow_write


class FakeClient:
    """Records uploads to each form (``HPD:WorkLog`` vs ``WOI:WorkInfo``)."""

    def __init__(self, status: str = 'Assigned') -> None:
        self.status = status
        self.incident_work_logs: list[object] = []
        self.work_infos: list[object] = []

    def _found(self) -> BmcEntryListResponse:
        data = {AR_FIELD_REQUEST_ID: 'REQ001', AR_FIELD_STATUS: self.status, AR_FIELD_SUBMITTER: 'svc_mosaico'}
        return BmcEntryListResponse(entries=[BmcEntry(values=BmcEntryValues(data=data))])

    async def search_incident(self, incident_number: str) -> BmcEntryListResponse:  # noqa: ARG002
        return self._found()

    async def search_work_order(self, work_order_id: str) -> BmcEntryListResponse:  # noqa: ARG002
        return self._found()

    async def post_incident_work_log(self, body: object) -> dict:
        self.incident_work_logs.append(body)
        return {}

    async def post_work_info(self, body: object) -> dict:
        self.work_infos.append(body)
        return {}


@pytest.fixture
def base(tmp_path: Path) -> Path:
    folder = tmp_path / 'shared'
    folder.mkdir()
    return folder


@pytest.fixture(autouse=True)
def _reset_handler_singleton() -> None:
    tool_handler.get_shared_handler.cache_clear()


def stage(base: Path, files: dict[str, bytes]) -> None:
    folder = base / STAGING_ID
    folder.mkdir()
    for name, content in files.items():
        (folder / name).write_bytes(content)
    manifest = {'files': [{'name': name, 'description': f'evidencia {name}'} for name in files]}
    (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def use_handler(monkeypatch: pytest.MonkeyPatch, client: FakeClient, settings: FakeSettings) -> None:
    handler = BaseToolHandler(client=client, settings=settings)  # type: ignore[arg-type]
    monkeypatch.setattr(tool_handler, 'get_shared_handler', lambda: handler)


async def run(ticket_type: str, ticket_number: str) -> dict:
    raw = await bmc_attach_staged_files.ainvoke(
        {'ticket_type': ticket_type, 'ticket_number': ticket_number, 'staging_id': STAGING_ID},
    )
    return json.loads(raw)


async def test_incident_files_go_to_the_incident_work_log(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'correo_original.eml': b'eml', 'captura.png': b'png'})
    client = FakeClient()
    use_handler(monkeypatch, client, FakeSettings(base))

    payload = await run('incident', 'INC1')

    assert payload['success'] is True
    assert len(client.incident_work_logs) == TWO_FILES
    assert client.work_infos == []


async def test_work_order_files_go_to_work_info(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'correo_original.eml': b'eml', 'captura.png': b'png'})
    client = FakeClient()
    use_handler(monkeypatch, client, FakeSettings(base))

    payload = await run('work_order', 'WO1')

    assert payload['success'] is True
    assert len(client.work_infos) == TWO_FILES
    assert client.incident_work_logs == []


async def test_oversized_file_is_not_uploaded_and_a_note_is_left(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'chico.txt': b'x', 'enorme.bin': b'0' * (MAX_BYTES + 1)})
    client = FakeClient()
    use_handler(monkeypatch, client, FakeSettings(base))

    payload = await run('incident', 'INC1')

    assert payload['success'] is True
    assert len(client.incident_work_logs) == FILE_PLUS_NOTE  # 1 archivo + 1 nota con lo omitido
    assert json.loads(payload['message'])['skipped'] == [{'name': 'enorme.bin', 'reason': 'too_large'}]


async def test_write_disabled_uploads_nothing(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'a.txt': b'x'})
    client = FakeClient()
    use_handler(monkeypatch, client, FakeSettings(base, allow_write=False))

    payload = await run('incident', 'INC1')

    assert payload['success'] is False
    assert client.incident_work_logs == []


async def test_closed_ticket_reports_failures(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'a.txt': b'x'})
    client = FakeClient(status='Closed')
    use_handler(monkeypatch, client, FakeSettings(base))

    payload = await run('incident', 'INC1')

    assert payload['success'] is False
    assert client.incident_work_logs == []


async def test_without_base_dir_nothing_is_read(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage(base, {'a.txt': b'x'})
    client = FakeClient()
    use_handler(monkeypatch, client, FakeSettings(None))

    payload = await run('incident', 'INC1')

    assert payload['success'] is False
    assert client.incident_work_logs == []


def test_tool_schema_exposes_only_ids_never_paths_or_content() -> None:
    assert set(bmc_attach_staged_files.args) == {'ticket_type', 'ticket_number', 'staging_id'}


def test_tool_is_registered_with_the_other_bmc_tools() -> None:
    names = {tool.name for tool in bmc_tools._ALL_BMC_TOOLS}  # noqa: SLF001
    assert 'bmc_attach_staged_files' in names
