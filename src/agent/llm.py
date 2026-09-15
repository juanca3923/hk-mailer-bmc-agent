"""LLM factory (Ollama, OpenAI, or Anthropic)."""

from __future__ import annotations

import functools
import os
import ssl
from collections.abc import Callable

import certifi
import httpx
from huggingface_hub import set_async_client_factory, set_client_factory
from huggingface_hub.utils._http import (
    async_hf_request_event_hook,
    async_hf_response_event_hook,
    hf_request_event_hook,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from config import Settings

# Anthropic prompt caching (system prompt, tools, long prefixes).
ANTHROPIC_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


@functools.cache
def _configure_huggingface_legacy_tls() -> None:
    """Relax OpenSSL's security level for huggingface_hub's HTTP client (idempotent).

    For corporate networks that TLS-intercept outbound HTTPS with a root CA using a weak
    key (<2048-bit RSA) or a SHA-1 signature: OpenSSL 3.x's default security level rejects
    that chain outright (``CA certificate key too weak``). Lowering to ``SECLEVEL=1`` keeps
    certificate verification on (uses ``SSL_CERT_FILE`` if set, else certifi) but stops
    rejecting on algorithm/key-size grounds. Never enable this in production; the correct
    fix is reissuing the corporate CA with a modern key.

    Idempotency is provided by ``functools.cache`` (a niladic function, so it runs its
    body only on the first call and returns the cached ``None`` on every call after),
    instead of a module-level flag.
    """
    cafile = os.environ.get("SSL_CERT_FILE") or certifi.where()

    def _build_ssl_context() -> ssl.SSLContext:
        ctx = ssl.create_default_context(cafile=cafile)
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        return ctx

    set_client_factory(
        lambda: httpx.Client(
            verify=_build_ssl_context(),
            event_hooks={"request": [hf_request_event_hook]},
            follow_redirects=True,
            timeout=None,
        )
    )
    set_async_client_factory(
        lambda: httpx.AsyncClient(
            verify=_build_ssl_context(),
            event_hooks={"request": [async_hf_request_event_hook], "response": [async_hf_response_event_hook]},
            follow_redirects=True,
            timeout=None,
        )
    )


def openai_prompt_cache_key(settings: Settings) -> str:
    """Return a stable OpenAI ``prompt_cache_key`` for this agent instance.

    Parameters
    ----
    settings : Settings
        Application settings (uses ``agent_slug``).

    Returns
    ----
    str
        Key passed to the OpenAI API to group prefix-cache hits.
    """
    slug = (settings.agent_slug or "agent_forge").strip()
    return f"{slug}-prompt-v1"


def openai_model_kwargs(settings: Settings) -> dict[str, str]:
    """Build OpenAI ``model_kwargs`` for server-side prompt caching."""
    return {"prompt_cache_key": openai_prompt_cache_key(settings)}


def get_openai_llm(settings: Settings, temperature: float = 0.6, stream: bool = False) -> BaseChatModel:
    """Get an OpenAI LLM for the given settings."""
    model_kwargs = openai_model_kwargs(settings)
    base = (settings.openai_base_url or "").strip()
    if base:
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key.strip(),
            temperature=temperature,
            streaming=stream,
            base_url=base,
            model_kwargs=model_kwargs,
        )
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key.strip(),
        temperature=temperature,
        streaming=stream,
        model_kwargs=model_kwargs,
    )


def get_huggingface_llm(settings: Settings, temperature: float = 0.6, stream: bool = False) -> BaseChatModel:
    """Get a Hugging Face chat model via the Inference Providers router.

    Uses ``HuggingFaceEndpoint`` with ``repo_id`` (no ``endpoint_url``), which routes the
    call through https://router.huggingface.co to whichever provider serves that model.
    Tool calling depends entirely on the chosen model/provider supporting it; unlike
    OpenAI/Anthropic this is not guaranteed for every ``HUGGINGFACE_MODEL``.

    Parameters
    ----
    settings : Settings
        Application settings.
    temperature : float
        Sampling temperature.
    stream : bool
        Whether to stream tokens.

    Returns
    ----
    BaseChatModel
        ``ChatHuggingFace`` wrapping the endpoint, with tool-calling support.
    """
    if settings.huggingface_allow_legacy_tls:
        _configure_huggingface_legacy_tls()

    bill_to = (settings.huggingface_bill_to or "").strip()
    endpoint = HuggingFaceEndpoint(
        repo_id=settings.huggingface_model,
        provider=(settings.huggingface_provider or "").strip() or None,
        huggingfacehub_api_token=settings.huggingface_api_key.strip(),
        temperature=temperature,
        do_sample=temperature > 0,
        streaming=stream,
        max_new_tokens=settings.huggingface_max_new_tokens,
        server_kwargs={"bill_to": bill_to} if bill_to else {},
    )
    return ChatHuggingFace(llm=endpoint)


def get_anthropic_llm(settings: Settings, temperature: float = 0.6, stream: bool = False) -> BaseChatModel:
    """Get an Anthropic LLM for the given settings, with prompt caching enabled."""
    llm = ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key.strip(),
        temperature=temperature,
        streaming=stream,
    )
    return llm.bind(cache_control=ANTHROPIC_CACHE_CONTROL)


def get_ollama_llm(settings: Settings, temperature: float = 0.6, stream: bool = False) -> BaseChatModel:
    """Get an Ollama LLM for the given settings."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_ctx=100000,
        streaming=stream,
        reasoning=True,
    )


def build_llm(settings: Settings) -> BaseChatModel:
    """Build the chat model for ``settings.llm_provider``.

    OpenAI and Anthropic instances enable provider-native prompt caching
    (static system prompt and tools benefit on repeated turns). Ollama is
    unchanged (local KV reuse only; no LangChain cache API).

    Parameters
    ----
    settings : Settings
        Application settings.

    Returns
    ----
    BaseChatModel
        Configured chat model.
    """
    llm_factories: dict[str, Callable[[Settings, float, bool], BaseChatModel]] = {
        "openai": get_openai_llm,
        "anthropic": get_anthropic_llm,
        "huggingface": get_huggingface_llm,
    }
    factory = llm_factories.get(settings.llm_provider, get_ollama_llm)
    return factory(settings, settings.llm_temperature, settings.stream)
