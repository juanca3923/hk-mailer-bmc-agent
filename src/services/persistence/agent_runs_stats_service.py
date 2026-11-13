"""Agregaciones y estadísticas sobre ejecuciones del agente (solo lectura)."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import func, select

from config import get_logger
from database.engine import get_session
from database.models import AgentRun


class AgentRunsStatsService:
    """Consultas agregadas sobre ``agent_runs`` (tokens, tiempos)."""

    def __init__(self) -> None:
        self.logger = get_logger()

    async def get_token_and_time_stats(
        self,
    ) -> dict[str, object]:
        """Totales de runs/tokens, runs con máximo de tokens y tiempo medio por solicitud."""
        async with get_session() as session:
            agg = await session.execute(
                select(
                    func.count(AgentRun.id).label("total_runs"),  # noqa: PGH003  # pylint: disable=not-callable
                    func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("sum_input"),
                    func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("sum_output"),
                )
            )
            row = agg.one()
            total_runs = int(row.total_runs or 0)
            sum_input = int(row.sum_input or 0)
            sum_output = int(row.sum_output or 0)

            avg_result = (
                await session.execute(
                    select(func.avg(AgentRun.total_time)).where(AgentRun.total_time.isnot(None))
                )
            ).scalar_one_or_none()
            avg_time_minutes = float(avg_result or 0)

            max_input_run = await session.execute(
                select(AgentRun)
                .where(AgentRun.total_input_tokens.isnot(None))
                .order_by(AgentRun.total_input_tokens.desc().nulls_last())
                .limit(1)
            )
            run_max_input = max_input_run.scalar_one_or_none()

            max_output_run = await session.execute(
                select(AgentRun)
                .where(AgentRun.total_output_tokens.isnot(None))
                .order_by(AgentRun.total_output_tokens.desc().nulls_last())
                .limit(1)
            )
            run_max_output = max_output_run.scalar_one_or_none()

        def run_tokens_summary(r: AgentRun | None) -> dict[str, object] | None:
            if r is None:
                return None
            return {
                "id": str(r.id),
                "total_input_tokens": r.total_input_tokens,
                "total_output_tokens": r.total_output_tokens,
            }

        stats: dict[str, object] = {
            "total_runs": total_runs,
            "total_input_tokens": sum_input,
            "total_output_tokens": sum_output,
            "run_with_max_input_tokens": run_tokens_summary(run_max_input),
            "run_with_max_output_tokens": run_tokens_summary(run_max_output),
            "average_time_per_request_seconds": avg_time_minutes * 60.0,
        }
        self.logger.debug(
            "get_token_and_time_stats: total_runs=%d input=%d output=%d",
            total_runs,
            sum_input,
            sum_output,
        )
        return stats


@lru_cache(maxsize=1)
def get_agent_runs_stats_service() -> AgentRunsStatsService:
    """Singleton del servicio de estadísticas de runs."""
    return AgentRunsStatsService()
