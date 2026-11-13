"""Unit tests for the ``get_current_date`` tool: Spanish formatting and timezone fallback."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from agent.internal_tools import datetime_tools
from agent.internal_tools.datetime_tools import DatetimeTools
from test.tool_lookup import tool_by_name


class FakeSettings:
    """Minimal stand-in for ``Settings`` exposing only ``agent_timezone``."""

    def __init__(self, agent_timezone: str) -> None:
        self.agent_timezone = agent_timezone


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tz_name: str) -> None:
    monkeypatch.setattr(datetime_tools.Settings, "load", staticmethod(lambda: FakeSettings(tz_name)))


def _patch_now(monkeypatch: pytest.MonkeyPatch, fixed: datetime) -> None:
    class FrozenDatetime(datetime):
        """``datetime`` subclass whose ``now()`` always returns a fixed instant."""

        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return fixed.astimezone(tz) if tz is not None else fixed

    monkeypatch.setattr(datetime_tools, "datetime", FrozenDatetime)


def test_get_current_date_formats_known_wednesday(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-10-07 is a Wednesday (miércoles) — pins the Spanish weekday/month tables."""
    _patch_settings(monkeypatch, "America/Bogota")
    fixed = datetime(2026, 10, 7, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
    _patch_now(monkeypatch, fixed)

    result = json.loads(tool_by_name(DatetimeTools.get_tools(), "get_current_date").invoke({}))

    assert result["date"] == "07/10/2026"
    assert result["day"] == fixed.day
    assert result["month"] == "octubre"
    assert result["year"] == fixed.year
    assert result["weekday"] == "miércoles"
    assert result["time"] == "09:30"
    assert result["short"] == "07/10/2026, miércoles, octubre"
    assert result["long"] == "miércoles 07 de octubre de 2026"


def test_get_current_date_falls_back_to_utc_on_invalid_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown/invalid ``AGENT_TIMEZONE`` must not crash the tool — fall back to UTC."""
    _patch_settings(monkeypatch, "Not/AZone")

    result = json.loads(tool_by_name(DatetimeTools.get_tools(), "get_current_date").invoke({}))

    assert result["timezone"] == "UTC"


def test_get_datetime_tools_returns_get_current_date() -> None:
    tools = DatetimeTools.get_tools()

    assert [t.name for t in tools] == ["get_current_date"]
