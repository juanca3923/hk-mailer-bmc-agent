"""Serialize DB rows to compact dicts for LLM context (memory tools)."""

from __future__ import annotations

import json

from database.models import AgentEvent, AgentRun, ChatMessage
from type_defs.dicts.agent_memory import AgentEventSummary, AgentRunSummary, ChatMessageSummary
from type_defs.dicts.json_types import JsonDict

CONTENT_PREVIEW_CHARS = 400


class MemorySerializer:
    """Serialize DB models to compact dicts for LLM context."""

    @staticmethod
    def run(run: AgentRun) -> AgentRunSummary:
        """Map an AgentRun to a serializable dict for the LLM."""
        return AgentRunSummary(
            id=str(run.id),
            chat_id=str(run.chat_id) if run.chat_id else None,
            status=run.status,
            user_message=run.user_message,
            final_reply=(run.final_reply or "")[:300] if run.final_reply else None,
            started_at=run.started_at.isoformat() if run.started_at else None,
            ended_at=run.ended_at.isoformat() if run.ended_at else None,
            total_time_seconds=round(run.total_time * 60, 1) if run.total_time else None,
            error_text=run.error_text,
        )

    @staticmethod
    def event(event: AgentEvent) -> AgentEventSummary:
        """Map an AgentEvent to a serializable dict."""
        return AgentEventSummary(
            event_type=event.event_type,
            ts=event.ts.isoformat(),
            payload_summary=MemorySerializer.payload_summary(event.payload),
        )

    @staticmethod
    def payload_summary(payload: JsonDict) -> dict[str, object]:
        """Return a compact payload summary for LLM context."""
        summary: dict[str, object] = {}

        def _str_field(value: str, limit: int = 200) -> str:
            return value[:limit] + "..." if len(value) > limit else value

        if "tool_name" in payload:
            summary["tool_name"] = payload["tool_name"]
        if "input" in payload:
            summary["input"] = _str_field(json.dumps(payload["input"]))
        if "result" in payload:
            summary["result"] = _str_field(str(payload["result"]))
        if "input_tokens" in payload:
            summary["input_tokens"] = payload["input_tokens"]
        if "output_tokens" in payload:
            summary["output_tokens"] = payload["output_tokens"]
        if "error" in payload:
            summary["error"] = payload["error"]
        return summary

    @staticmethod
    def chat_message(msg: ChatMessage) -> ChatMessageSummary:
        """Map a ChatMessage to a compact dict."""
        content = msg.content
        return ChatMessageSummary(
            role=msg.role,
            message_type=msg.message_type,
            content=content[:CONTENT_PREVIEW_CHARS] + "..." if len(content) > CONTENT_PREVIEW_CHARS else content,
            ts=msg.ts.isoformat(),
            agent_run_id=str(msg.agent_run_id) if msg.agent_run_id else None,
        )
