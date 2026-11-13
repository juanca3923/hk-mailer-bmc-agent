"""``BaseToolHandler.load_attachment`` solo lee archivos dentro de ``BMC_ATTACHMENT_BASE_DIR``.

Sin este confinamiento un texto malicioso (p. ej. en un correo) podría inducir al agente a adjuntar al
ticket cualquier archivo legible del contenedor (``/etc/passwd``, un ``.env``, etc.).
"""

from pathlib import Path

import pytest

from constants.bmc import (
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED,
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED,
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND,
    USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE,
)
from exception.mcp import MCPClientError
from services.bmc.tool_handler import BaseToolHandler

MAX_BYTES = 1024


class FakeSettings:
    """Minimal stand-in for ``BmcSettings`` with the attachment-related fields."""

    def __init__(self, attachment_base_dir: Path | None, max_attachment_bytes: int = MAX_BYTES) -> None:
        self.attachment_base_dir = attachment_base_dir
        self.max_attachment_bytes = max_attachment_bytes


def make_handler(base: Path | None, max_bytes: int = MAX_BYTES) -> BaseToolHandler:
    return BaseToolHandler(client=object(), settings=FakeSettings(base, max_bytes))  # type: ignore[arg-type]


@pytest.fixture
def base(tmp_path: Path) -> Path:
    folder = tmp_path / 'staging'
    folder.mkdir()
    return folder


def test_file_inside_base_is_loaded(base: Path) -> None:
    (base / 'captura.png').write_bytes(b'png-bytes')
    part = make_handler(base).load_attachment(str(base / 'captura.png'))
    assert part.filename == 'captura.png'
    assert part.content == b'png-bytes'


def test_file_in_subfolder_of_base_is_loaded(base: Path) -> None:
    sub = base / 'abc'
    sub.mkdir()
    (sub / 'log.txt').write_bytes(b'x')
    assert make_handler(base).load_attachment(str(sub / 'log.txt')).filename == 'log.txt'


def test_file_outside_base_is_rejected(base: Path, tmp_path: Path) -> None:
    secret = tmp_path / 'secret.env'
    secret.write_bytes(b'TOKEN=1')
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(secret))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED


def test_dotdot_traversal_is_rejected(base: Path, tmp_path: Path) -> None:
    (tmp_path / 'secret.env').write_bytes(b'TOKEN=1')
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(base / '..' / 'secret.env'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED


def test_symlink_inside_base_pointing_outside_is_rejected(base: Path, tmp_path: Path) -> None:
    secret = tmp_path / 'secret.env'
    secret.write_bytes(b'TOKEN=1')
    (base / 'innocent.txt').symlink_to(secret)
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(base / 'innocent.txt'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED


def test_base_not_configured_rejects_everything(base: Path) -> None:
    (base / 'a.txt').write_bytes(b'x')
    with pytest.raises(MCPClientError) as exc:
        make_handler(None).load_attachment(str(base / 'a.txt'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED


def test_missing_file_inside_base_is_not_found(base: Path) -> None:
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(base / 'nope.txt'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND


def test_directory_is_not_found(base: Path) -> None:
    (base / 'carpeta').mkdir()
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(base / 'carpeta'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND


def test_file_over_limit_is_too_large(base: Path) -> None:
    (base / 'big.bin').write_bytes(b'0' * (MAX_BYTES + 1))
    with pytest.raises(MCPClientError) as exc:
        make_handler(base).load_attachment(str(base / 'big.bin'))
    assert exc.value.message == USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE
