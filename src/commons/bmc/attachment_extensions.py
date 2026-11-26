"""Pure checks for which attachment extensions may be uploaded to a ticket."""

from __future__ import annotations

from constants.bmc.staged import ALWAYS_ALLOWED_EXTENSIONS, DEFAULT_ALLOWED_EXTENSIONS


def parse_extensions(raw: str) -> frozenset[str]:
    """Turn a comma-separated list into a set of lowercase extensions without the leading dot.

    Parameters
    ----------
    raw : str
        Value of ``TICKET_FILES_ALLOWED_EXTENSIONS``; empty or blank means the default list.

    Returns
    -------
    frozenset[str]
        Normalised extensions (case, spaces and a leading dot are ignored).
    """
    text = raw if raw.strip() else DEFAULT_ALLOWED_EXTENSIONS
    items = (item.strip().lstrip('.').strip().lower() for item in text.split(','))
    return frozenset(item for item in items if item)


def is_extension_allowed(file_name: str, allowed: frozenset[str] | None) -> bool:
    """Tell whether the final extension of ``file_name`` may be uploaded.

    Parameters
    ----------
    file_name : str
        File name (only the text after its last dot counts).
    allowed : frozenset[str] | None
        Allowed extensions; ``None`` disables the filter. The original email (``.eml``) is always allowed.

    Returns
    -------
    bool
        ``False`` for names without extension or with one that is not allowed.
    """
    if allowed is None:
        return True
    extension = file_name.strip().rsplit('.', 1)[-1].strip().lower() if '.' in file_name else ''
    return bool(extension) and extension in (allowed | ALWAYS_ALLOWED_EXTENSIONS)
