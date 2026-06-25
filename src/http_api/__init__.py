"""Servicio HTTP de AgentForge.

La aplicación FastAPI y el punto de entrada Uvicorn están en ``http_api.app``.
Este ``__init__`` está vacío a propósito: importar ``app`` aquí al cargar el
paquete provocaba un ciclo con ``commons`` (``commons.agent_http`` importa
``http_api.state`` mientras ``commons`` aún se inicializa).

Usar siempre ``from http_api.app import app`` o la ruta de objeto ``http_api.app:app``.
"""

from __future__ import annotations

__all__: list[str] = []
