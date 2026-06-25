"""Tipos de dominio para el cliente A2A (peers remotos)."""

from __future__ import annotations

from dataclasses import dataclass

from type_defs.dicts.json_types import JsonDict


@dataclass(frozen=True, slots=True)
class PeerInfo:
    """Un agente remoto descubierto vía Agent Card."""

    index: int
    base_url: str
    assistant_id: str
    name: str
    card: JsonDict
