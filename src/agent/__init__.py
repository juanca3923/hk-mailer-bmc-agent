"""Núcleo del agente y CLI.

El punto de entrada ``main`` de la consola está en ``agent.cli``; no se reexporta
aquí para evitar importaciones circulares al cargar ``agent.runtime.runner``.
"""

from __future__ import annotations

from agent.agent import build_agent

__all__ = ["build_agent"]
