"""Registro del cliente Langfuse para que el callback de LangChain resuelva credenciales."""

from __future__ import annotations

import base64
import threading
from typing import Optional

import httpx
from langfuse import Langfuse
from langfuse._version import __version__ as langfuse_version
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from config import get_logger
from config.settings import Settings

logger = get_logger()

lock = threading.Lock()
initialized_public_keys: set[str] = set()

# Timeout corto para el cliente HTTP de Langfuse (trazas).
LANGFUSE_CLIENT_TIMEOUT_S = 5


def _build_insecure_span_exporter(
    public_key: str,
    secret_key: str,
    host: str,
) -> OTLPSpanExporter:
    """Build an OTLPSpanExporter that skips TLS verification.

    Required when Langfuse is self-hosted with a self-signed certificate and
    LANGFUSE_SSL_VERIFY=false.

    SSL bypass requires patching ``exporter._certificate_file = False`` after creation.
    ``OTLPSpanExporter._export`` passes ``verify=self._certificate_file`` explicitly on
    every ``session.post()``, which overrides any ``session.verify`` setting.
    Passing ``certificate_file=False`` to the constructor does NOT work because the
    internal assignment uses ``certificate_file or default``, which evaluates ``False``
    as falsy and falls through to the default ``True``.

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
    exporter = OTLPSpanExporter(
        endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
        headers={
            "Authorization": f"Basic {token}",
            "x-langfuse-sdk-name": "python",
            "x-langfuse-sdk-version": langfuse_version,
            "x-langfuse-public-key": public_key,
        },
        timeout=LANGFUSE_CLIENT_TIMEOUT_S,
    )
    # ``_export`` passes ``verify=self._certificate_file`` to session.post(), so
    # patching the attribute is the only reliable way to disable SSL verification.
    exporter._certificate_file = False  # type: ignore[assignment]  # pylint: disable=protected-access
    return exporter


def ensure_langfuse_tracing_client(settings: Settings) -> None:
    """Instancia ``Langfuse`` una vez por ``public_key`` para registrar el recurso OTEL.

    El ``CallbackHandler`` de LangChain usa ``get_client(public_key=...)``, que requiere
    que exista un ``Langfuse`` previo con esas credenciales (host/secret viven en el
    gestor de recursos interno).

    Cuando ``LANGFUSE_SSL_VERIFY=false``, crea un ``OTLPSpanExporter`` con
    ``_certificate_file=False`` (parche post-creación) para que las trazas no fallen
    por SSL con servidores self-hosted que usan certificado autofirmado.
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
