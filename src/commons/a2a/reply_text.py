"""Extract visible text from A2A ``message/send`` JSON-RPC result payloads."""

from __future__ import annotations

from typing import cast

from type_defs.dicts.json_types import JsonDict


def first_stripped_text_from_parts(parts_raw: object) -> str:
    """Return the first non-empty ``kind=text`` part in a ``parts`` list."""
    if not isinstance(parts_raw, list):
        return ""
    for part in parts_raw:
        if not isinstance(part, dict):
            continue
        if part.get("kind") != "text":
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def text_from_a2a_parts_container(container: JsonDict) -> str:
    """Extract text from a dict that exposes a ``parts`` list (artifact or message)."""
    return first_stripped_text_from_parts(container.get("parts", []) or [])


def text_from_a2a_artifacts(artifacts_raw: object) -> str:
    """Scan ``artifacts`` and return the first non-empty text part found."""
    if not isinstance(artifacts_raw, list):
        return ""
    for artifact in artifacts_raw:
        if not isinstance(artifact, dict):
            continue
        text = text_from_a2a_parts_container(cast(JsonDict, artifact))
        if text:
            return text
    return ""


def text_from_a2a_status(status_raw: object) -> str:
    """Extract text from ``status.message.parts`` when present."""
    if not isinstance(status_raw, dict):
        return ""
    message_raw = status_raw.get("message", {}) or {}
    if not isinstance(message_raw, dict):
        return ""
    return text_from_a2a_parts_container(cast(JsonDict, message_raw))


def extract_a2a_reply_text(result_obj: JsonDict) -> str:
    """Extract reply text from ``message/send`` result (artifacts, then status.message)."""
    text = text_from_a2a_artifacts(result_obj.get("artifacts", []) or [])
    if text:
        return text
    return text_from_a2a_status(result_obj.get("status", {}) or [])
