"""Protocolos de callable usados en el agente IA."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from type_defs.dicts.json_types import JsonDict


class LogFn(Protocol):
    """Callable de logging estructurado para eventos de ejecución del agente.

    Se usa como tipo del parámetro `log_fn` en AgentRunCallbackHandler para
    permitir inyectar cualquier función de logging sin acoplarse a una
    implementación concreta.
    """

    def __call__(
        self,
        *,
        event_type: str,
        agent_run_id: UUID,
        payload: JsonDict,
    ) -> None: ...
