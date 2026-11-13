"""Constantes del agente: prompts, LLM, observabilidad, vistas previas y fechas."""

from __future__ import annotations

GRAPH_ATTR_A2A_REGISTRY = "_agent_forge_a2a_registry"


# Anthropic prompt caching (system prompt, tools, long prefixes).
ANTHROPIC_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


# Nombre del archivo de extensiones del prompt (instrucciones de memoria/tools internas).
# Debe vivir en la misma carpeta que el prompt principal (raíz del proyecto).
BASE_PROMPT_FILENAME = "base.prompt.md"


LANGFUSE_FETCH_TIMEOUT_S = 5


# Timeout corto para el cliente HTTP de Langfuse (trazas).
LANGFUSE_CLIENT_TIMEOUT_S = 5


SEARCH_PREVIEW_MAX_LEN = 120


CONTENT_PREVIEW_CHARS = 400


WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
