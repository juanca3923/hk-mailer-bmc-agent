"""Tests del cliente A2A (parseo de respuestas)."""

from __future__ import annotations

from typing import cast

from commons.a2a_reply_text import extract_a2a_reply_text
from type_defs.dicts.json_types import JsonDict


def test_extract_from_artifacts() -> None:
    result = cast(
        JsonDict,
        {
            "artifacts": [{"parts": [{"kind": "text", "text": "  salida  "}]}],
            "contextId": "ctx-1",
            "id": "task-1",
        },
    )
    assert extract_a2a_reply_text(result) == "salida"


def test_extract_from_status_message() -> None:
    result = cast(
        JsonDict,
        {
            "status": {
                "message": {
                    "parts": [{"kind": "text", "text": "desde status"}],
                },
            },
        },
    )
    assert extract_a2a_reply_text(result) == "desde status"


def test_extract_empty() -> None:
    assert extract_a2a_reply_text(cast(JsonDict, {})) == ""
