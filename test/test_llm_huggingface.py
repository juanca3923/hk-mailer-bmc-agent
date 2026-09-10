"""`get_huggingface_llm` con dobles simples de `HuggingFaceEndpoint`/`ChatHuggingFace`.

No abre conexión real: reemplaza ambas clases por dobles que solo capturan los
argumentos con los que fueron invocadas.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from agent import llm as llm_module

_DEFAULT_MAX_NEW_TOKENS = 2048
_DEFAULT_TEMPERATURE = 0.6
_CUSTOM_MAX_NEW_TOKENS = 512


class _FakeEndpoint:
    """Captura los kwargs con los que se construyó, sin llamar a HF real."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _FakeChatHuggingFace:
    """Captura el `llm` (endpoint) con el que se envolvió."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm


def _fake_settings(**overrides: Any) -> SimpleNamespace:
    base = {
        "huggingface_model": "meta-llama/Llama-3.3-70B-Instruct",
        "huggingface_provider": "",
        "huggingface_api_key": "hf_test_token",
        "huggingface_bill_to": "",
        "huggingface_max_new_tokens": _DEFAULT_MAX_NEW_TOKENS,
        "huggingface_allow_legacy_tls": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patch_hf_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "HuggingFaceEndpoint", _FakeEndpoint)
    monkeypatch.setattr(llm_module, "ChatHuggingFace", _FakeChatHuggingFace)


def test_defaults_translate_to_none_provider_and_empty_server_kwargs() -> None:
    settings = _fake_settings()
    chat = llm_module.get_huggingface_llm(settings, temperature=_DEFAULT_TEMPERATURE, stream=False)

    assert isinstance(chat, _FakeChatHuggingFace)
    endpoint = chat.llm
    assert isinstance(endpoint, _FakeEndpoint)
    assert endpoint.kwargs["repo_id"] == settings.huggingface_model
    assert endpoint.kwargs["provider"] is None
    assert endpoint.kwargs["server_kwargs"] == {}
    assert endpoint.kwargs["max_new_tokens"] == _DEFAULT_MAX_NEW_TOKENS
    assert endpoint.kwargs["temperature"] == _DEFAULT_TEMPERATURE
    assert endpoint.kwargs["do_sample"] is True
    assert endpoint.kwargs["streaming"] is False


def test_bill_to_and_provider_are_forwarded_when_set() -> None:
    settings = _fake_settings(huggingface_provider="together", huggingface_bill_to="my-org")
    chat = llm_module.get_huggingface_llm(settings, temperature=_DEFAULT_TEMPERATURE, stream=False)

    endpoint = chat.llm
    assert endpoint.kwargs["provider"] == "together"
    assert endpoint.kwargs["server_kwargs"] == {"bill_to": "my-org"}


def test_max_new_tokens_uses_configured_value() -> None:
    settings = _fake_settings(huggingface_max_new_tokens=_CUSTOM_MAX_NEW_TOKENS)
    chat = llm_module.get_huggingface_llm(settings, temperature=_DEFAULT_TEMPERATURE, stream=False)

    assert chat.llm.kwargs["max_new_tokens"] == _CUSTOM_MAX_NEW_TOKENS


def test_do_sample_false_when_temperature_zero() -> None:
    settings = _fake_settings()
    chat = llm_module.get_huggingface_llm(settings, temperature=0.0, stream=False)

    assert chat.llm.kwargs["do_sample"] is False


def test_legacy_tls_configured_only_when_flag_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[None] = []
    monkeypatch.setattr(llm_module, "_configure_huggingface_legacy_tls", lambda: calls.append(None))

    llm_module.get_huggingface_llm(_fake_settings(huggingface_allow_legacy_tls=False), _DEFAULT_TEMPERATURE, False)
    assert len(calls) == 0

    llm_module.get_huggingface_llm(_fake_settings(huggingface_allow_legacy_tls=True), _DEFAULT_TEMPERATURE, False)
    assert len(calls) == 1
