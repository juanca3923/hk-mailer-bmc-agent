"""TypedDicts para el store cross-thread de AgentForge (AgentPostgresStore)."""

from __future__ import annotations

from typing import TypedDict

from type_defs.dicts.json_types import JsonDict


class MemoryFactEntry(TypedDict):
    """Hecho persistido en el store (una entrada de agent_memory_facts).

    Usado como valor de retorno al inspeccionar el store desde las tools o la API.
    """

    namespace: str
    key: str
    value: JsonDict
    updated_at: str


class MemoryFactSearchResult(TypedDict):
    """Resultado de búsqueda ILIKE en el store cross-thread."""

    namespace: str
    key: str
    value: JsonDict
