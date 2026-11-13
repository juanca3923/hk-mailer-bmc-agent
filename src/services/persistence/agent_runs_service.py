"""Agent run persistence: lifecycle writes and read queries for tools/API."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import get_logger
from database.engine import get_session
from database.models import AgentEvent, AgentRun
from type_defs.enums.domain_literals import (
    RUN_STATUS_CANCELLED,
    RUN_STATUS_ERROR,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    TurnStatus,
)
from type_defs.enums.event_types import EVENT_LLM_END


class AgentRunsService:
    """Persist and query agent execution runs."""

    def __init__(self) -> None:
        self.logger = get_logger()

    # ------------------------------------------------------------------
    # Write (runner lifecycle)
    # ------------------------------------------------------------------

    async def create_run(
        self,
        *,
        agent_run_id: UUID,
        user_message: str,
        chat_id: UUID | None = None,
    ) -> None:
        """Crea un run en estado running, opcionalmente asociado a un chat."""
        async with get_session() as session:
            run = AgentRun(
                id=agent_run_id,
                user_message=user_message,
                status=RUN_STATUS_RUNNING,
                chat_id=chat_id,
            )
            session.add(run)
            await session.commit()
        self.logger.debug("create_run: id=%s chat_id=%s", agent_run_id, chat_id)

    async def _finish(
        self,
        *,
        agent_run_id: UUID,
        status: TurnStatus,
        final_reply: str | None,
        error_text: str | None,
    ) -> None:
        """Cierra el run con estado terminal y métricas derivadas de eventos llm_end."""
        now = datetime.now(timezone.utc)
        async with get_session() as session:
            run = await session.get(AgentRun, agent_run_id)
            if run is None:
                self.logger.debug("_finish: run not found id=%s", agent_run_id)
                return
            if run.started_at is None:
                total_time_minutes = None
            else:
                total_time_minutes = (now - run.started_at).total_seconds() / 60.0

            result = await session.execute(
                select(AgentEvent).where(
                    AgentEvent.agent_run_id == agent_run_id,
                    AgentEvent.event_type == EVENT_LLM_END,
                )
            )
            events = result.scalars().all()
            total_input_tokens = sum(int(cast("int | str", e.payload.get("input_tokens") or 0)) for e in events)
            total_output_tokens = sum(int(cast("int | str", e.payload.get("output_tokens") or 0)) for e in events)
            run.ended_at = now
            run.total_time = total_time_minutes
            run.status = status
            run.final_reply = final_reply
            run.error_text = error_text
            run.total_input_tokens = total_input_tokens if events else None
            run.total_output_tokens = total_output_tokens if events else None
            await session.commit()
        self.logger.debug("_finish: id=%s status=%s", agent_run_id, status)

    async def finish_run_success(self, *, agent_run_id: UUID, final_reply: str) -> None:
        """Marca el run como completado con respuesta final."""
        await self._finish(
            agent_run_id=agent_run_id,
            status=RUN_STATUS_SUCCESS,
            final_reply=final_reply,
            error_text=None,
        )

    async def finish_run_cancelled(self, *, agent_run_id: UUID) -> None:
        """Marca el run como cancelado."""
        await self._finish(
            agent_run_id=agent_run_id,
            status=RUN_STATUS_CANCELLED,
            final_reply=None,
            error_text=None,
        )

    async def finish_run_error(self, *, agent_run_id: UUID, error_text: str) -> None:
        """Marca el run como fallido con texto de error."""
        await self._finish(
            agent_run_id=agent_run_id,
            status=RUN_STATUS_ERROR,
            final_reply=None,
            error_text=error_text,
        )

    # ------------------------------------------------------------------
    # Read (memory tools and REST API)
    # ------------------------------------------------------------------

    async def get_active_run(self) -> AgentRun | None:
        """Most recent run with status=running."""
        async with get_session() as session:
            result = await session.execute(
                select(AgentRun)
                .where(AgentRun.status == RUN_STATUS_RUNNING)
                .order_by(AgentRun.started_at.desc())
                .limit(1)
            )
            active = result.scalar_one_or_none()
        self.logger.debug("get_active_run: found=%s", active is not None)
        return active

    async def list_recent_runs(self, limit: int) -> list[AgentRun]:
        """Latest runs ordered by started_at descending."""
        async with get_session() as session:
            result = await session.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit))
            runs = list(result.scalars().all())
        self.logger.debug("list_recent_runs: limit=%d count=%d", limit, len(runs))
        return runs

    async def get_run_with_events(
        self,
        run_uuid: UUID,
    ) -> tuple[AgentRun, list[AgentEvent]] | None:
        """Run by id and its events ordered by ts ascending."""
        async with get_session() as session:
            run = await session.get(AgentRun, run_uuid)
            if run is None:
                self.logger.debug("get_run_with_events: not found id=%s", run_uuid)
                return None
            events_result = await session.execute(
                select(AgentEvent).where(AgentEvent.agent_run_id == run_uuid).order_by(AgentEvent.ts.asc())
            )
            events = list(events_result.scalars().all())
        self.logger.debug("get_run_with_events: id=%s events=%d", run_uuid, len(events))
        return run, events

    async def get_last_run_with_events(
        self,
    ) -> tuple[AgentRun, list[AgentEvent]] | None:
        """Último run por ``started_at`` descendente, con eventos ordenados por ``ts`` ascendente."""
        async with get_session() as session:
            result = await session.execute(
                select(AgentRun).options(selectinload(AgentRun.events)).order_by(AgentRun.started_at.desc()).limit(1)
            )
            run = result.scalar_one_or_none()
            if run is None:
                self.logger.debug("get_last_run_with_events: no runs")
                return None
            events = sorted(run.events, key=lambda e: e.ts)
        self.logger.debug("get_last_run_with_events: id=%s events=%d", run.id, len(events))
        return run, events


@lru_cache(maxsize=1)
def get_agent_runs_service() -> AgentRunsService:
    """Singleton del servicio de runs del agente."""
    return AgentRunsService()
