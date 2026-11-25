"""Registro del cliente Langfuse para que el callback de LangChain resuelva credenciales."""

from __future__ import annotations

import base64
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import Any, Optional
from uuid import UUID

import httpx
from langfuse import Langfuse, propagate_attributes
from langfuse._version import __version__ as langfuse_version
from opentelemetry.exporter.http.transport._requests import RequestsHTTPTransport
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from config import get_logger
from config.settings import Settings
from constants.agent import LANGFUSE_CLIENT_TIMEOUT_S

logger = get_logger()

TRACE_VALUE_MAX_CHARS = 200
CALLER_KEYS = ('caller_agent', 'caller_chat_id', 'caller_run_id')

lock = threading.Lock()
initialized_public_keys: set[str] = set()


def _build_insecure_span_exporter(
    public_key: str,
    secret_key: str,
    host: str,
) -> OTLPSpanExporter:
    """Build an OTLPSpanExporter that skips TLS verification.

    Required when Langfuse is self-hosted with a self-signed certificate and
    LANGFUSE_SSL_VERIFY=false.

    Since ``opentelemetry-exporter-otlp-proto-http`` 1.45 the exporter delegates HTTP to a
    transport object whose ``verify`` flag is fixed at construction time (it overwrites
    ``session.verify``), and ``_certificate_file`` no longer exists. Neither
    ``certificate_file=False`` (falsy, falls back to ``True``) nor a custom ``requests``
    session can disable verification, so a ``RequestsHTTPTransport(verify=False)`` is
    injected through the exporter's ``_transport`` keyword.

    Parameters
    ----------
    public_key : str
        Langfuse project public key.
    secret_key : str
        Langfuse project secret key.
    host : str
        Langfuse base URL (e.g. ``https://host/langfuse``).

    Returns
    -------
    OTLPSpanExporter
        Exporter pointing at ``{host}/api/public/otel/v1/traces`` with SSL disabled.
    """
    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return OTLPSpanExporter(
        endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
        headers={
            "Authorization": f"Basic {token}",
            "x-langfuse-sdk-name": "python",
            "x-langfuse-sdk-version": langfuse_version,
            "x-langfuse-public-key": public_key,
        },
        timeout=LANGFUSE_CLIENT_TIMEOUT_S,
        _transport=RequestsHTTPTransport(verify=False),  # noqa: S501 — opt-in vía LANGFUSE_SSL_VERIFY=false
    )


def ensure_langfuse_tracing_client(settings: Settings) -> None:
    """Instancia ``Langfuse`` una vez por ``public_key`` para registrar el recurso OTEL.

    El ``CallbackHandler`` de LangChain usa ``get_client(public_key=...)``, que requiere
    que exista un ``Langfuse`` previo con esas credenciales (host/secret viven en el
    gestor de recursos interno).

    Cuando ``LANGFUSE_SSL_VERIFY=false``, crea un ``OTLPSpanExporter`` con un transporte
    ``requests`` sin verificación TLS para que las trazas no fallen por SSL con servidores
    self-hosted que usan certificado autofirmado.
    """
    if not settings.langfuse_tracing_ready:
        return
    public_key = settings.langfuse_public_key.strip()
    secret_key = settings.langfuse_secret_key.strip()
    host = settings.langfuse_host.strip()
    with lock:
        if public_key in initialized_public_keys:
            return

        span_exporter: Optional[OTLPSpanExporter] = None
        if not settings.langfuse_ssl_verify:
            span_exporter = _build_insecure_span_exporter(public_key, secret_key, host)

        Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            timeout=LANGFUSE_CLIENT_TIMEOUT_S,
            httpx_client=httpx.Client(verify=settings.langfuse_ssl_verify),
            span_exporter=span_exporter,
        )
        initialized_public_keys.add(public_key)
        logger.info("cliente Langfuse registrado para trazas")


def _ascii(value: object) -> str:
    """Return ``value`` as US-ASCII text of at most 200 characters (Langfuse drops anything else)."""
    return str(value).encode('ascii', 'ignore').decode('ascii')[:TRACE_VALUE_MAX_CHARS]


def build_trace_attributes(
    *,
    agent_slug: str,
    chat_id: UUID,
    run_id: UUID,
    mode: str,
    caller: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build the Langfuse trace attributes of one run: name, session, tags and metadata.

    The session is the chat, so every turn of a conversation is a trace of the same Langfuse session; when a
    calling agent sent its own chat (A2A), that one becomes the session so both agents' traces are grouped.
    No email, subject or message text ever goes in here.

    Parameters
    ----------
    agent_slug : str
        Agent identifier (part of the trace name and tags).
    chat_id : UUID
        Chat of this run.
    run_id : UUID
        Agent run id.
    mode : str
        How the run started: ``chat``, ``awake`` or ``a2a``.
    caller : Mapping[str, str] | None, optional
        ``caller_agent``, ``caller_chat_id`` and ``caller_run_id`` sent by the calling agent.

    Returns
    -------
    dict[str, Any]
        Keyword arguments for ``langfuse.propagate_attributes``.
    """
    metadata = {'agent_run_id': _ascii(run_id), 'own_chat_id': _ascii(chat_id)}
    session_id = _ascii(chat_id)
    for key in CALLER_KEYS:
        value = (caller or {}).get(key)
        if value:
            metadata[key] = _ascii(value)
    if metadata.get('caller_chat_id'):
        session_id = metadata['caller_chat_id']
    return {
        'session_id': session_id,
        'trace_name': _ascii(f'{agent_slug}:{mode}'),
        'tags': [_ascii(agent_slug), _ascii(mode)],
        'metadata': metadata,
    }


def trace_attributes(
    *,
    settings: Settings,
    chat_id: UUID,
    run_id: UUID,
    mode: str,
    caller: Mapping[str, str] | None = None,
) -> AbstractContextManager[Any]:
    """Return the context that propagates the run's attributes to every Langfuse span inside it.

    Wrap the graph invocation with it: the LangChain callback handler then nests its spans under one trace that
    carries the name, session, tags and metadata. Without Langfuse credentials it does nothing.

    Parameters
    ----------
    settings : Settings
        Application settings (Langfuse credentials and agent slug).
    chat_id : UUID
        Chat of this run.
    run_id : UUID
        Agent run id.
    mode : str
        ``chat``, ``awake`` or ``a2a``.
    caller : Mapping[str, str] | None, optional
        Data of the calling agent, when there is one.

    Returns
    -------
    AbstractContextManager[Any]
        ``propagate_attributes(...)`` or a no-op context.
    """
    if not settings.langfuse_tracing_ready:
        return nullcontext()
    return propagate_attributes(
        **build_trace_attributes(
            agent_slug=settings.agent_slug, chat_id=chat_id, run_id=run_id, mode=mode, caller=caller
        )
    )
