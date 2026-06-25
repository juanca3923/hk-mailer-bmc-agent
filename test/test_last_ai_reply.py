"""Tests de :class:`commons.last_ai_reply.ReplyExtractor`."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from commons.last_ai_reply import ReplyExtractor


def test_from_messages_extracts_text_from_anthropic_style_blocks() -> None:
    msg = AIMessage(content=[{"type": "text", "text": "Estado del servidor OK", "index": 0}])
    assert ReplyExtractor().from_messages([msg]) == "Estado del servidor OK"


def test_from_messages_plain_string_unchanged() -> None:
    msg = AIMessage(content="Hola desde Ollama")
    assert ReplyExtractor().from_messages([msg]) == "Hola desde Ollama"
