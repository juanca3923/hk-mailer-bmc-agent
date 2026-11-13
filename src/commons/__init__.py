"""Código compartido (helpers) para CLI y servicio HTTP del agente.

Los entrypoints concretos se importan desde submódulos (p. ej. ``http_api.lifecycle``)
para evitar importaciones circulares al cargar ``commons``.
"""

from __future__ import annotations

from commons.text.utils import TextUtils

__all__ = ["TextUtils"]
