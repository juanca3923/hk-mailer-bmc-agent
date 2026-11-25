"""Carga del prompt en dos capas: reglas de oro fijas (system) + comportamiento (base, Langfuse o archivo)."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent import prompts
from exception import AgentConfigError

SYSTEM_TEXT = 'REGLAS DE ORO: no inventes nada.'
LOCAL_BASE = 'BASE LOCAL: guia de atencion.'
LANGFUSE_BASE = 'BASE LANGFUSE: guia de atencion.'


def _settings(
    tmp_path: Path,
    *,
    system_env: str = '',
    langfuse_name: str = '',
    system_file: str | None = SYSTEM_TEXT,
    local_base: str | None = LOCAL_BASE,
) -> Any:
    if system_file is not None:
        (tmp_path / 'system.promt.md').write_text(system_file, encoding='utf-8')
    if local_base is not None:
        (tmp_path / 'base.prompt.md').write_text(local_base, encoding='utf-8')
    return SimpleNamespace(
        system_prompt_env=system_env,
        langfuse_prompt_name=langfuse_name,
        langfuse_prompt_label='latest',
        resolved_system_prompt_file=lambda: tmp_path / 'system.promt.md',
        repo_root=lambda: tmp_path,
    )


@pytest.fixture(autouse=True)
def _no_skills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts, 'build_skills_catalog_xml', lambda: '')


def test_system_comes_from_the_file_and_base_from_the_local_file_without_langfuse(tmp_path: Path) -> None:
    prompt = prompts.load_system_prompt_for_settings(_settings(tmp_path))

    assert prompt == f'{SYSTEM_TEXT}\n\n{LOCAL_BASE}'


def test_the_system_prompt_can_be_injected_by_environment(tmp_path: Path) -> None:
    settings = _settings(tmp_path, system_env='REGLAS POR ENTORNO', system_file='')

    prompt = prompts.load_system_prompt_for_settings(settings)

    assert prompt.startswith('REGLAS POR ENTORNO')
    assert SYSTEM_TEXT not in prompt


def test_the_system_prompt_never_comes_from_langfuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(prompts, 'fetch_prompt_from_langfuse', lambda _s, name: calls.append(name) or LANGFUSE_BASE)

    prompt = prompts.load_system_prompt_for_settings(_settings(tmp_path, langfuse_name='base-mailer'))

    assert calls == ['base-mailer']
    assert prompt.startswith(SYSTEM_TEXT)


def test_an_empty_system_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(AgentConfigError, match='vac'):
        prompts.load_system_prompt_for_settings(_settings(tmp_path, system_file='   '))


def test_a_missing_system_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(AgentConfigError):
        prompts.load_system_prompt_for_settings(_settings(tmp_path, system_file=None))


def test_base_from_langfuse_replaces_the_local_file_and_is_never_added_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompts, 'fetch_prompt_from_langfuse', lambda _s, _n: LANGFUSE_BASE)
    read_local: list[Path] = []
    original = prompts.read_optional
    monkeypatch.setattr(prompts, 'read_optional', lambda p: read_local.append(p) or original(p))

    prompt = prompts.load_system_prompt_for_settings(_settings(tmp_path, langfuse_name='base-mailer'))

    assert prompt == f'{SYSTEM_TEXT}\n\n{LANGFUSE_BASE}'
    assert LOCAL_BASE not in prompt
    assert read_local == []


@pytest.mark.parametrize('fetched', ['', '   '])
def test_when_langfuse_gives_nothing_the_local_base_is_used_with_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, fetched: str
) -> None:
    monkeypatch.setattr(prompts, 'fetch_prompt_from_langfuse', lambda _s, _n: fetched)
    caplog.set_level(logging.WARNING)

    prompt = prompts.load_system_prompt_for_settings(_settings(tmp_path, langfuse_name='base-mailer'))

    assert prompt == f'{SYSTEM_TEXT}\n\n{LOCAL_BASE}'
    assert any('base' in r.getMessage().lower() and 'local' in r.getMessage().lower() for r in caplog.records)


def test_without_any_base_source_it_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts, 'fetch_prompt_from_langfuse', lambda _s, _n: '')

    with pytest.raises(AgentConfigError, match='base'):
        prompts.load_system_prompt_for_settings(_settings(tmp_path, langfuse_name='base-mailer', local_base=None))


def test_each_layer_appears_once_in_order_and_skills_go_last(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts, 'build_skills_catalog_xml', lambda: '<skills>\nuna => skill\n</skills>')

    prompt = prompts.load_system_prompt_for_settings(_settings(tmp_path))

    assert prompt.count(SYSTEM_TEXT) == 1
    assert prompt.count(LOCAL_BASE) == 1
    assert prompt.index(SYSTEM_TEXT) < prompt.index(LOCAL_BASE) < prompt.index('<skills>')
    assert prompt.endswith('</skills>')
