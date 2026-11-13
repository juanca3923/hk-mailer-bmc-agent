"""Constantes de configuración: patrones, límites y niveles de log."""

from __future__ import annotations

import logging
import re

AGENT_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*\Z")


# Nombre lógico del archivo sin extensión: letra/número inicial, resto alfanumérico + _ -
SKILL_STEM_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


# Tope de caracteres devueltos al LLM al leer una guía completa
DEFAULT_MAX_SKILL_CHARS = 12_000


LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}
