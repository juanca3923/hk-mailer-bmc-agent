"""LLM factory (Ollama, OpenAI, or Anthropic)."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from config import Settings

# Anthropic prompt caching (system prompt, tools, long prefixes).
ANTHROPIC_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


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
    temperature = 0.6
    stream = settings.stream

    if settings.llm_provider == "openai":
        return get_openai_llm(settings, temperature, stream)

    if settings.llm_provider == "anthropic":
        llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.strip(),
            temperature=temperature,
            streaming=stream,
        )
        return llm.bind(cache_control=ANTHROPIC_CACHE_CONTROL)

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_ctx=100000,
        streaming=stream,
        reasoning=True,
    )
