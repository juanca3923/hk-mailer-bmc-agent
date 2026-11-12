"""``StagedFilesAttacher``: sube a un ticket los archivos que otro agente dejó en la carpeta compartida.

El mailer escribe ``<BMC_ATTACHMENT_BASE_DIR>/<staging_id>/`` con los archivos y un ``manifest.json``
(``{"files": [{"name": ..., "description": ...}]}``). El BMC solo recibe el ``staging_id``: nunca los bytes.
"""

import json
from pathlib import Path

import pytest

from bmc.libs.constants import (
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED,
    USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE,
    USER_ERROR_MESSAGE_WRITE_DISABLED,
)
from bmc.libs.helpers.staged_files import StagedFilesAttacher
from bmc.type_defs.outputs import BaseOutput

STAGING_ID = '0b9f2c1e-7a54-4c1d-9d0e-3f6a1b2c4d5e'
MAX_BYTES = 100


class FakeWriter:
    """Records uploads and notes; ``failures`` maps a file name to the output to return."""

    def __init__(self, failures: dict[str, BaseOutput] | None = None) -> None:
        self.failures = failures or {}
        self.attached: list[tuple[str, str]] = []
        self.notes: list[str] = []

    async def attach(self, file_path: str, note_text: str) -> BaseOutput:
        name = Path(file_path).name
        if name in self.failures:
            return self.failures[name]
        self.attached.append((name, note_text))
        return BaseOutput(success=True, message='ok')

    async def note(self, note_text: str) -> BaseOutput:
        self.notes.append(note_text)
        return BaseOutput(success=True, message='ok')


@pytest.fixture
def base(tmp_path: Path) -> Path:
    folder = tmp_path / 'shared'
    folder.mkdir()
    return folder


def stage(base: Path, files: dict[str, bytes], manifest: object | None = None) -> None:
    """Create ``<base>/<STAGING_ID>`` with ``files`` and a manifest (default: one entry per file)."""
    folder = base / STAGING_ID
    folder.mkdir()
    for name, content in files.items():
        (folder / name).write_bytes(content)
    if manifest is None:
        manifest = {'files': [{'name': name, 'description': f'desc {name}'} for name in files]}
    (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def make(base: Path | None, writer: FakeWriter) -> StagedFilesAttacher:
    return StagedFilesAttacher(writer, base_dir=base, max_bytes=MAX_BYTES)


def report(result: BaseOutput) -> dict[str, list]:
    return json.loads(result.message)


async def test_uploads_every_file_in_manifest_order_with_its_description(base: Path) -> None:
    stage(base, {'correo_original.eml': b'eml', 'captura.png': b'png'})
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert result.success is True
    assert writer.attached == [('correo_original.eml', 'desc correo_original.eml'), ('captura.png', 'desc captura.png')]
    assert report(result)['attached'] == ['correo_original.eml', 'captura.png']
    assert writer.notes == []


async def test_file_without_description_uses_its_name_as_note(base: Path) -> None:
    stage(base, {'a.log': b'x'}, manifest={'files': [{'name': 'a.log'}]})
    writer = FakeWriter()
    await make(base, writer).attach(STAGING_ID)
    assert writer.attached == [('a.log', 'a.log')]


async def test_oversized_file_is_skipped_and_one_note_lists_it(base: Path) -> None:
    stage(base, {'ok.png': b'x', 'grande.bin': b'0' * (MAX_BYTES + 1), 'otro.bin': b'0' * (MAX_BYTES + 5)})
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert [name for name, _ in writer.attached] == ['ok.png']
    assert len(writer.notes) == 1
    assert 'grande.bin' in writer.notes[0]
    assert 'otro.bin' in writer.notes[0]
    skipped = report(result)['skipped']
    assert {(item['name'], item['reason']) for item in skipped} == {
        ('grande.bin', 'too_large'),
        ('otro.bin', 'too_large'),
    }
    assert result.success is True


async def test_file_listed_but_missing_is_skipped(base: Path) -> None:
    stage(base, {'esta.txt': b'x'}, manifest={'files': [{'name': 'esta.txt'}, {'name': 'falta.txt'}]})
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert [name for name, _ in writer.attached] == ['esta.txt']
    assert {(item['name'], item['reason']) for item in report(result)['skipped']} == {('falta.txt', 'missing')}
    assert 'falta.txt' in writer.notes[0]


@pytest.mark.parametrize('name', ['../secreto.txt', 'sub/a.txt', '/etc/passwd', '..', '.', '.oculto', 'a\\b.txt'])
async def test_manifest_names_with_path_parts_are_never_uploaded(base: Path, name: str) -> None:
    stage(base, {'bueno.txt': b'x'}, manifest={'files': [{'name': 'bueno.txt'}, {'name': name}]})
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert [n for n, _ in writer.attached] == ['bueno.txt']
    assert {(item['name'], item['reason']) for item in report(result)['skipped']} == {(name, 'invalid_name')}


async def test_symlink_in_staging_folder_is_not_uploaded(base: Path, tmp_path: Path) -> None:
    secret = tmp_path / 'secret.env'
    secret.write_bytes(b'TOKEN=1')
    stage(base, {'bueno.txt': b'x'}, manifest={'files': [{'name': 'bueno.txt'}, {'name': 'enlace.txt'}]})
    (base / STAGING_ID / 'enlace.txt').symlink_to(secret)
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert [n for n, _ in writer.attached] == ['bueno.txt']
    assert {item['name'] for item in report(result)['skipped']} == {'enlace.txt'}


@pytest.mark.parametrize('staging_id', ['../x', '/etc', 'a/b', '', 'corto', 'x' * 65, 'con espacio 1234'])
async def test_invalid_staging_id_is_rejected_without_touching_disk_or_ticket(base: Path, staging_id: str) -> None:
    writer = FakeWriter()

    result = await make(base, writer).attach(staging_id)

    assert result.success is False
    assert writer.attached == []
    assert writer.notes == []


async def test_missing_staging_folder_fails(base: Path) -> None:
    writer = FakeWriter()
    result = await make(base, writer).attach(STAGING_ID)
    assert result.success is False
    assert writer.attached == []


INVALID_MANIFESTS = ['no es json', '{"files": "nope"}', '[]', '{"files": [{"description": "sin nombre"}]}']


@pytest.mark.parametrize('content', INVALID_MANIFESTS)
async def test_invalid_manifest_fails(base: Path, content: str) -> None:
    stage(base, {'a.txt': b'x'})
    (base / STAGING_ID / 'manifest.json').write_text(content, encoding='utf-8')
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert result.success is False
    assert writer.attached == []


async def test_base_dir_not_configured_fails(base: Path) -> None:
    stage(base, {'a.txt': b'x'})
    result = await make(None, FakeWriter()).attach(STAGING_ID)
    assert result.success is False
    assert result.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED


async def test_writer_failure_is_reported_and_the_rest_continue(base: Path) -> None:
    stage(base, {'a.txt': b'x', 'b.txt': b'x', 'c.txt': b'x'})
    writer = FakeWriter(failures={'b.txt': BaseOutput(success=False, message='Error: ticket cerrado')})

    result = await make(base, writer).attach(STAGING_ID)

    assert [n for n, _ in writer.attached] == ['a.txt', 'c.txt']
    assert result.success is False
    assert report(result)['failed'] == [{'name': 'b.txt', 'message': 'Error: ticket cerrado'}]


async def test_write_disabled_stops_at_the_first_file(base: Path) -> None:
    stage(base, {'a.txt': b'x', 'b.txt': b'x'})
    disabled = BaseOutput(success=False, message=USER_ERROR_MESSAGE_WRITE_DISABLED)
    writer = FakeWriter(failures={'a.txt': disabled, 'b.txt': disabled})

    result = await make(base, writer).attach(STAGING_ID)

    assert result.success is False
    assert result.message == USER_ERROR_MESSAGE_WRITE_DISABLED
    assert writer.attached == []
    assert writer.notes == []


async def test_writer_reporting_too_large_counts_as_skipped_not_failed(base: Path) -> None:
    """BMC rejects by its own limit even if the pre-check passed (e.g. file grew)."""
    stage(base, {'a.txt': b'x'})
    too_large = BaseOutput(success=False, message=USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE)
    writer = FakeWriter(failures={'a.txt': too_large})

    result = await make(base, writer).attach(STAGING_ID)

    assert result.success is True
    assert {(i['name'], i['reason']) for i in report(result)['skipped']} == {('a.txt', 'too_large')}
    assert 'a.txt' in writer.notes[0]


async def test_empty_manifest_is_success_and_creates_no_note(base: Path) -> None:
    stage(base, {}, manifest={'files': []})
    writer = FakeWriter()

    result = await make(base, writer).attach(STAGING_ID)

    assert result.success is True
    assert report(result)['attached'] == []
    assert writer.notes == []
