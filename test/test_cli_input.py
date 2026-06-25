"""Tests for CLI stdin sanitization."""

from __future__ import annotations

from agent.cli import CLI_MAX_USER_INPUT_CHARS, sanitize_repl_user_input


def test_sanitize_strips_and_removes_nul() -> None:
    assert sanitize_repl_user_input("  hola\x00mundo  ") == "holamundo"


def test_sanitize_enforces_max_length() -> None:
    raw = "a" * (CLI_MAX_USER_INPUT_CHARS + 100)
    assert len(sanitize_repl_user_input(raw)) == CLI_MAX_USER_INPUT_CHARS
