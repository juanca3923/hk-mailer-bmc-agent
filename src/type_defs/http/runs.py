"""Schemas para endpoints de runs y estadísticas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from type_defs.dicts.json_types import JsonDict


class EventDetail(BaseModel):
    """Un evento de una run (tipo, timestamp, payload)."""

    event_type: str
    ts: datetime
    payload: JsonDict


class RunDetailResponse(BaseModel):
    """Detalle de una run con sus eventos."""

    id: str
    started_at: datetime
    ended_at: datetime | None
    total_time: float | None
    user_message: str
    final_reply: str | None
    status: str
    error_text: str | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    events: list[EventDetail]


class RunTokensSummary(BaseModel):
    """Resumen de tokens de una run (id + input/output)."""

    id: str
    total_input_tokens: int | None
    total_output_tokens: int | None


class StatsResponse(BaseModel):
    """Estadísticas agregadas de runs: tokens y tiempo."""

    total_runs: int
    total_input_tokens: int
    total_output_tokens: int
    run_with_max_input_tokens: RunTokensSummary | None
    run_with_max_output_tokens: RunTokensSummary | None
    average_time_per_request_seconds: float
