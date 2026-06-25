"""Schemas Pydantic para el estado del agente."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

StatusAgent = Literal["DOWN", "UP", "DOING_TASK"]


class StatusResponse(BaseModel):
    """Respuesta de GET /status."""

    status: str
