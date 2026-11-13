"""End the run deterministically when a ticket tool reports an unverified requester.

A person missing from BMC is a business outcome, not a failure: the tool message starts with
``NOT_VERIFIED_MARKER``. Instead of trusting the model to stop, this middleware answers with the structured
summary and jumps to the end, so the model is not called again (no retries, no workarounds).
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, ToolMessage

from constants.bmc.messages import NOT_VERIFIED_MARKER

_EMAIL_PATTERN = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@.,;]+')


def _plain_message(content: Any) -> str:
    """Return the tool's ``message`` text, unwrapping the ``{"success": ..., "message": ...}`` JSON when present."""
    text = content if isinstance(content, str) else str(content)
    try:
        payload = json.loads(text)
    except ValueError:
        return text
    message = payload.get('message') if isinstance(payload, dict) else None
    return message if isinstance(message, str) else text


def build_not_verified_summary(tool_message: str) -> str:
    """Build the structured summary for an unverified requester.

    Parameters
    ----------
    tool_message : str
        Plain message of the tool (already without JSON), which contains ``NOT_VERIFIED_MARKER``.

    Returns
    -------
    str
        Summary lines in the format the automatic mode of the prompt defines.
    """
    found = _EMAIL_PATTERN.search(tool_message)
    requester = found.group(0) if found else '—'
    return f'Ticket creado: —\nSolicitante: {requester}\n{tool_message}'


class NotVerifiedStop(AgentMiddleware):
    """Finish the run when the last tool result says the requester is not verified."""

    @staticmethod
    def _stop(state: Any) -> dict[str, Any] | None:
        messages = list(state['messages'])
        last = messages[-1] if messages else None
        if not isinstance(last, ToolMessage):
            return None
        message = _plain_message(last.content)
        if NOT_VERIFIED_MARKER not in message:
            return None
        return {'messages': [AIMessage(content=build_not_verified_summary(message))], 'jump_to': 'end'}

    @hook_config(can_jump_to=['end'])
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Answer with the summary and jump to the end after a not-verified tool result."""
        return self._stop(state)

    @hook_config(can_jump_to=['end'])
    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Async twin of ``before_model``."""
        return self._stop(state)
