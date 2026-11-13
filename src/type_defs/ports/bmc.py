"""Contratos de BMC: guarda de escritura y escritor de un ticket."""

from __future__ import annotations

from typing import Protocol

from type_defs.models.bmc.outputs import BaseOutput


class WriteGate(Protocol):
    """Handler surface needed to check that writes are enabled."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""


class TicketWriter(Protocol):
    """Writes to one specific ticket (incident or work order)."""

    async def attach(self, file_path: str, note_text: str) -> BaseOutput:
        """Upload ``file_path`` as a work log entry with ``note_text``."""

    async def note(self, note_text: str) -> BaseOutput:
        """Add a work log note without attachment."""
