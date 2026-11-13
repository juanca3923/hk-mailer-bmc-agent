"""Internal tool exposing the current date/time, localized to the agent's timezone.

The LLM has no notion of "today" beyond training data, so any reasoning about
relative dates ("mañana", "hace dos días") or timestamps written into a ticket
needs a real anchor. This reads the container's system clock and converts it
to ``AGENT_TIMEZONE`` (default ``America/Bogota``) — it never guesses or
reuses a date already present in the conversation.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import BaseTool

from agent.internal_tools.base import ToolSet
from config import Settings, get_logger
from constants.agent import MONTHS_ES, WEEKDAYS_ES

logger = get_logger()


def _resolve_timezone() -> ZoneInfo:
    """Load ``AGENT_TIMEZONE`` and fall back to UTC on an unknown/invalid name."""
    tz_name = (Settings.load().agent_timezone or 'America/Bogota').strip()
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError, ValueError:
        logger.warning('get_current_date: zona horaria inválida %r, usando UTC', tz_name)
        return ZoneInfo('UTC')


class DatetimeTools(ToolSet):
    """Current date/time tool anchored to the agent's timezone."""

    def get_current_date(self) -> str:
        """Return the current date and time in the agent's configured timezone.

        Call this whenever "today", "now", a relative date, or a ticket
        timestamp matters — never assume or infer the date from the
        conversation or from training data; the container's system clock
        (converted to ``AGENT_TIMEZONE``) is the only source of truth.

        Returns
        -------
        str
            JSON with ``date`` (``DD/MM/YYYY``), ``day``, ``month`` (Spanish,
            lowercase), ``year``, ``weekday`` (Spanish, lowercase), ``time``
            (``HH:MM``), ``timezone``, ``short`` (e.g.
            ``"07/10/2026, lunes, octubre"``) and ``long`` (e.g.
            ``"lunes 07 de octubre de 2026"``).
        """
        now = datetime.now(_resolve_timezone())
        weekday_name = WEEKDAYS_ES[now.weekday()]
        month_name = MONTHS_ES[now.month - 1]
        date_short = now.strftime('%d/%m/%Y')
        result = {
            'date': date_short,
            'day': now.day,
            'month': month_name,
            'year': now.year,
            'weekday': weekday_name,
            'time': now.strftime('%H:%M'),
            'timezone': str(now.tzinfo),
            'short': f'{date_short}, {weekday_name}, {month_name}',
            'long': f'{weekday_name} {now.day:02d} de {month_name} de {now.year}',
        }
        logger.info('get_current_date: %s %s (%s)', result['date'], result['time'], result['timezone'])
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Return the datetime tools to register in the graph."""
        tools = DatetimeTools()
        return [
            tools.build(
                tools.get_current_date,
                name='get_current_date',
                description=(
                    "Return the current date and time in the agent's configured timezone. Call "
                    "this whenever 'today', 'now', a relative date, or a ticket timestamp matters "
                    '— never assume or infer the date from the conversation or training data.'
                ),
            ),
        ]
