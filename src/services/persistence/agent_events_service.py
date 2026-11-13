"""Persistencia de eventos de traza por ejecución (callbacks LLM/tools)."""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from config import get_logger
from database.engine import get_session
from database.models import AgentEvent
from exception import AgentError
from type_defs.enums.event_types import AgentEventType
from type_defs.models.common.json_types import JsonDict


class AgentEventsService:
    """Inserta filas en ``agent_events`` sin interrumpir el agente si falla la BD."""

    def __init__(self) -> None:
        self.logger = get_logger()

    async def insert_event(
        self,
        *,
        agent_run_id: UUID,
        event_type: AgentEventType,
        payload: JsonDict,
    ) -> None:
        """Inserta un evento de traza; los fallos de persistencia solo se registran en log."""
        try:
            async with get_session() as session:
                session.add(
                    AgentEvent(
                        agent_run_id=agent_run_id,
                        event_type=event_type,
                        payload=payload,
                    )
                )
                await session.commit()
        except AgentError as error:
            self.logger.error(
                "Error al insertar evento %s (run=%s): %s", event_type, agent_run_id, type(error).__name__
            )


@lru_cache(maxsize=1)
def get_agent_events_service() -> AgentEventsService:
    """Singleton del servicio de eventos del agente."""
    return AgentEventsService()
