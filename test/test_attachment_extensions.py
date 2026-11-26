"""Allowed attachment extensions: same variable and values as the mailer (``TICKET_FILES_ALLOWED_EXTENSIONS``)."""

import pytest

from commons.bmc.attachment_extensions import is_extension_allowed, parse_extensions
from config.bmc_settings import BmcSettings
from constants.bmc.staged import DEFAULT_ALLOWED_EXTENSIONS


def test_parse_ignores_case_spaces_and_leading_dot() -> None:
    assert parse_extensions(' PDF, .Png ,docx,, ') == frozenset({'pdf', 'png', 'docx'})


def test_empty_value_uses_the_mailer_default_list() -> None:
    assert parse_extensions('') == parse_extensions(DEFAULT_ALLOWED_EXTENSIONS)
    assert 'pdf' in parse_extensions('   ')


@pytest.mark.parametrize('name', ['a.pdf', 'A.PDF', 'foto.final.Png', 'correo_original.eml'])
def test_allowed_names(name: str) -> None:
    assert is_extension_allowed(name, parse_extensions('pdf,png')) is True


@pytest.mark.parametrize('name', ['virus.exe', 'sin_extension', 'archivo.', 'a.pdf.exe', 'script.js'])
def test_rejected_names(name: str) -> None:
    assert is_extension_allowed(name, parse_extensions('pdf,png')) is False


def test_original_email_is_always_allowed_even_if_not_listed() -> None:
    assert is_extension_allowed('correo_original.eml', parse_extensions('pdf')) is True


def test_no_filter_when_allowed_is_none() -> None:
    assert is_extension_allowed('lo-que-sea.bin', None) is True


def test_settings_read_the_shared_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('TICKET_FILES_ALLOWED_EXTENSIONS', 'PDF, .zip')
    monkeypatch.setenv('BMC_BASE_URL', 'https://x.example')
    monkeypatch.setenv('BMC_USERNAME', 'u')
    monkeypatch.setenv('BMC_PASSWORD', 'p')
    monkeypatch.setenv('BMC_ASSIGNEE_DISPLAY_NAME', 'a')
    assert BmcSettings().attachment_extensions == frozenset({'pdf', 'zip'})
