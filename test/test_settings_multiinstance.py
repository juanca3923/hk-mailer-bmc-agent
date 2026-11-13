"""Comportamiento de Settings para multi-instancia (slug, A2A, prompt)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings

_ENV_KEYS = (
    "AGENT_SLUG",
    "AGENT_DISPLAY_NAME",
    "AGENT_CARD_DESCRIPTION",
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_PATH",
    "A2A_ASSISTANT_ID",
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "LANGFUSE_PROMPT_NAME",
)


@pytest.fixture(autouse=True)
def _clear_multiinstance_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que el entorno del desarrollador anule los valores de cada test."""
    monkeypatch.setenv("HTTP_PORT", "8000")
    for name in _ENV_KEYS:
        monkeypatch.delenv(name, raising=False)
    # Tras delenv, Settings() sigue exigiendo el resto de campos sin default del modelo.
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:9b")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    monkeypatch.setenv("LANGFUSE_HOST", "")
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "")


def test_agent_slug_must_match_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SLUG", "BadSlug")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("AGENT_SLUG", "9start")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("AGENT_SLUG", "a-b")
    with pytest.raises(ValidationError):
        Settings()


def test_effective_a2a_assistant_id_falls_back_to_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SLUG", "mybot")
    s = Settings()
    assert s.effective_a2a_assistant_id == "mybot"


def test_effective_a2a_assistant_id_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SLUG", "mybot")
    monkeypatch.setenv("A2A_ASSISTANT_ID", "legacy_id")
    s = Settings()
    assert s.effective_a2a_assistant_id == "legacy_id"


def test_effective_agent_display_name_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SLUG", "my_bot")
    s = Settings()
    assert s.effective_agent_display_name == "My Bot"


def test_effective_agent_card_description_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_CARD_DESCRIPTION", "  Descripción personalizada.  ")
    s = Settings()
    assert s.effective_agent_card_description == "Descripción personalizada."


def test_effective_agent_card_description_default_states_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SLUG", "mybot")
    s = Settings()
    description = s.effective_agent_card_description
    assert "mybot" in description
    assert "correo real" in description
    assert "quedan abiertos" in description


def test_normalized_a2a_peer_configs_requires_url_pipe_agent_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("A2A_PEER_URLS", "http://localhost:9000")
    assert Settings().normalized_a2a_peer_configs() == []

    monkeypatch.setenv("A2A_PEER_URLS", "http://localhost:9000|remote_bot")
    assert Settings().normalized_a2a_peer_configs() == [("http://localhost:9000", "remote_bot")]

    monkeypatch.setenv(
        "A2A_PEER_URLS",
        "http://a:1|id1,http://solo-url,http://b:2|id2,  |bad ,http://c:3|id3",
    )
    assert Settings().normalized_a2a_peer_configs() == [
        ("http://a:1", "id1"),
        ("http://b:2", "id2"),
        ("http://c:3", "id3"),
    ]


def test_resolved_system_prompt_file_relative_to_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_PROMPT_PATH", "system.promt.md")
    s = Settings()
    p = s.resolved_system_prompt_file()
    assert p.name == "system.promt.md"
    assert p.parent == Settings.repo_root()


def test_resolved_system_prompt_file_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "custom.md"
    f.write_text("prompt body", encoding="utf-8")
    monkeypatch.setenv("SYSTEM_PROMPT_PATH", str(f))
    s = Settings()
    assert s.resolved_system_prompt_file() == f


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_huggingface_provider_requires_api_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "huggingface")
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_MODEL", raising=False)
    with pytest.raises(ValidationError):
        Settings()

    monkeypatch.setenv("HUGGINGFACE_API_KEY", "hf_test")
    with pytest.raises(ValidationError):
        Settings()

    monkeypatch.setenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    Settings()


_DEFAULT_LLM_TEMPERATURE = 0.6
_DEFAULT_HF_MAX_NEW_TOKENS = 2048
_CUSTOM_LLM_TEMPERATURE = 0.2
_CUSTOM_HF_MAX_NEW_TOKENS = 512


def test_llm_temperature_and_huggingface_max_new_tokens_default_and_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("HUGGINGFACE_MAX_NEW_TOKENS", raising=False)
    s = Settings()
    assert s.llm_temperature == _DEFAULT_LLM_TEMPERATURE
    assert s.huggingface_max_new_tokens == _DEFAULT_HF_MAX_NEW_TOKENS

    monkeypatch.setenv("LLM_TEMPERATURE", str(_CUSTOM_LLM_TEMPERATURE))
    monkeypatch.setenv("HUGGINGFACE_MAX_NEW_TOKENS", str(_CUSTOM_HF_MAX_NEW_TOKENS))
    s = Settings()
    assert s.llm_temperature == _CUSTOM_LLM_TEMPERATURE
    assert s.huggingface_max_new_tokens == _CUSTOM_HF_MAX_NEW_TOKENS


def test_langfuse_prompt_name_requires_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "my-prompt")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    with pytest.raises(ValidationError):
        Settings()
