"""Código compartido (helpers) para CLI y servicio HTTP del agente.

Los entrypoints concretos se importan desde submódulos (p. ej. ``commons.agent_http``)
para evitar importaciones circulares al cargar ``commons``.
"""

from __future__ import annotations

from commons.utils import TextUtils

__all__ = ["TextUtils"]
