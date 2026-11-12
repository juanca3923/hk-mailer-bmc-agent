"""Attach to a BMC ticket the files another agent staged in the shared folder.

The producer (``hk-mailer-agent``) writes ``<attachment_base_dir>/<staging_id>/`` with the files and a
``manifest.json`` of the form ``{"files": [{"name": "...", "description": "..."}]}``. This agent only
receives the ``staging_id``: file bytes never travel through any LLM context.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from bmc.libs.constants import (
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED,
    USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE,
    USER_ERROR_MESSAGE_STAGING_INVALID_ID,
    USER_ERROR_MESSAGE_STAGING_INVALID_MANIFEST,
    USER_ERROR_MESSAGE_STAGING_NOT_FOUND,
    USER_ERROR_MESSAGE_WRITE_DISABLED,
)
from bmc.type_defs.outputs import BaseOutput

logger = logging.getLogger(__name__)

STAGING_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')
MANIFEST_FILE_NAME = 'manifest.json'
REASON_TOO_LARGE = 'too_large'
REASON_MISSING = 'missing'
REASON_INVALID_NAME = 'invalid_name'
REASON_NOT_ALLOWED = 'not_allowed'
# Reasons worth telling the ticket reader about; the rest are internal inconsistencies.
NOTE_REASONS = (REASON_TOO_LARGE, REASON_MISSING)
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024


class TicketWriter(Protocol):
    """Writes to one specific ticket (incident or work order)."""

    async def attach(self, file_path: str, note_text: str) -> BaseOutput:
        """Upload ``file_path`` as a work log entry with ``note_text``."""

    async def note(self, note_text: str) -> BaseOutput:
        """Add a work log note without attachment."""


@dataclass
class _Outcome:
    """Accumulated result of one staging folder."""

    attached: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    sizes: dict[str, int] = field(default_factory=dict)


def format_size(size: int) -> str:
    """Return a short human-readable size (``KB`` below 1 MB, ``MB`` above).

    Parameters
    ----------
    size : int
        Size in bytes.

    Returns
    -------
    str
        For example ``'512 KB'`` or ``'10.5 MB'``.
    """
    if size < BYTES_PER_MB:
        return f'{size / BYTES_PER_KB:.0f} KB'
    return f'{size / BYTES_PER_MB:.1f} MB'


def is_plain_file_name(name: str) -> bool:
    """Tell whether ``name`` is a bare file name (no directories, no hidden files).

    Parameters
    ----------
    name : str
        Candidate name taken from a manifest.

    Returns
    -------
    bool
        ``False`` for empty names, separators (``/`` or ``\\``), ``.``/``..`` and dotfiles.
    """
    forbidden_chars = ('/', '\\', '\x00')
    return bool(name) and not name.startswith('.') and not any(char in name for char in forbidden_chars)


class StagedFilesAttacher:
    """Upload every file of a staging folder to a ticket, skipping what cannot be attached.

    Attributes
    ----------
    _writer : TicketWriter
        Adapter bound to one ticket.
    _base_dir : Path | None
        Shared folder root (``BMC_ATTACHMENT_BASE_DIR``); ``None`` disables the feature.
    _max_bytes : int
        Largest file BMC accepts.
    """

    def __init__(self, writer: TicketWriter, base_dir: Path | None, max_bytes: int) -> None:
        self._writer = writer
        self._base_dir = base_dir
        self._max_bytes = max_bytes

    async def attach(self, staging_id: str) -> BaseOutput:
        """Attach the files listed in ``<base>/<staging_id>/manifest.json``.

        Files over the size limit or missing are not uploaded; one work log note lists them so the
        ticket reader knows they exist. Other per-file failures do not stop the remaining files.

        Parameters
        ----------
        staging_id : str
            Folder name produced by the staging agent.

        Returns
        -------
        BaseOutput
            ``success=True`` with a JSON report (``attached``, ``skipped``, ``failed``) when nothing
            failed; ``success=False`` for an invalid request or when any upload failed.
        """
        opened = self._open_staging(staging_id)
        if isinstance(opened, BaseOutput):
            return opened
        folder, entries = opened
        outcome = _Outcome()
        for name, description in entries:
            stop = await self._process_entry(folder, name, description, outcome)
            if stop is not None:
                return stop
        await self._note_skipped(outcome)
        report = {'attached': outcome.attached, 'skipped': outcome.skipped, 'failed': outcome.failed}
        return BaseOutput(success=not outcome.failed, message=json.dumps(report, ensure_ascii=False))

    def _open_staging(self, staging_id: str) -> tuple[Path, list[tuple[str, str]]] | BaseOutput:
        """Validate the request and read the manifest, or return the failure output."""
        failure: BaseOutput | None = None
        folder = Path()
        if self._base_dir is None:
            failure = BaseOutput(success=False, message=USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED)
        elif not STAGING_ID_PATTERN.fullmatch(staging_id):
            failure = BaseOutput(success=False, message=USER_ERROR_MESSAGE_STAGING_INVALID_ID)
        else:
            folder = (self._base_dir / staging_id).resolve()
            if not folder.is_dir() or not folder.is_relative_to(self._base_dir.resolve()):
                failure = BaseOutput(success=False, message=USER_ERROR_MESSAGE_STAGING_NOT_FOUND)
        if failure is not None:
            return failure
        entries = self._read_manifest(folder)
        if entries is None:
            return BaseOutput(success=False, message=USER_ERROR_MESSAGE_STAGING_INVALID_MANIFEST)
        return folder, entries

    @staticmethod
    def _read_manifest(folder: Path) -> list[tuple[str, str]] | None:
        """Return ``(name, description)`` pairs, or ``None`` when the manifest is missing/invalid."""
        try:
            data = json.loads((folder / MANIFEST_FILE_NAME).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        files = data.get('files') if isinstance(data, dict) else None
        if not isinstance(files, list):
            return None
        entries: list[tuple[str, str]] = []
        for item in files:
            name = item.get('name') if isinstance(item, dict) else None
            if not isinstance(name, str) or not name:
                return None
            description = item.get('description')
            text = description.strip() if isinstance(description, str) else ''
            entries.append((name, text or name))
        return entries

    async def _process_entry(self, folder: Path, name: str, description: str, outcome: _Outcome) -> BaseOutput | None:
        """Upload one file; return a ``BaseOutput`` only when the whole run must stop."""
        reason = self._skip_reason(folder, name, outcome)
        if reason is not None:
            outcome.skipped.append({'name': name, 'reason': reason})
            return None
        result = await self._writer.attach(str(folder / name), description)
        if result.success:
            outcome.attached.append(name)
        elif result.message == USER_ERROR_MESSAGE_WRITE_DISABLED:
            return result
        elif result.message == USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE:
            outcome.skipped.append({'name': name, 'reason': REASON_TOO_LARGE})
        else:
            outcome.failed.append({'name': name, 'message': result.message})
        return None

    def _skip_reason(self, folder: Path, name: str, outcome: _Outcome) -> str | None:
        """Return why ``name`` must not be uploaded, or ``None`` when it can be."""
        reason: str | None = None
        path = folder / name
        if not is_plain_file_name(name):
            reason = REASON_INVALID_NAME
        elif path.is_symlink() or (path.exists() and not path.resolve().is_relative_to(folder)):
            reason = REASON_NOT_ALLOWED
        elif not path.is_file():
            reason = REASON_MISSING
        else:
            size = path.stat().st_size
            outcome.sizes[name] = size
            if size > self._max_bytes:
                reason = REASON_TOO_LARGE
        return reason

    async def _note_skipped(self, outcome: _Outcome) -> None:
        """Leave one ticket note listing the files that could not be attached."""
        lines = [
            f'- {item["name"]}: {self._describe_reason(item["name"], item["reason"], outcome)}'
            for item in outcome.skipped
            if item['reason'] in NOTE_REASONS
        ]
        if not lines:
            return
        text = f'No se adjuntaron {len(lines)} archivo(s) del correo:\n' + '\n'.join(lines)
        result = await self._writer.note(text)
        if not result.success:
            logger.warning('No se pudo dejar la nota de adjuntos omitidos: %s', result.message)

    def _describe_reason(self, name: str, reason: str, outcome: _Outcome) -> str:
        """Human-readable reason for the ticket note."""
        if reason == REASON_TOO_LARGE:
            size = format_size(outcome.sizes[name]) if name in outcome.sizes else 'tamaño desconocido'
            return f'supera el tamaño máximo permitido ({size}; máximo {format_size(self._max_bytes)})'
        return 'archivo no encontrado en la carpeta compartida'
