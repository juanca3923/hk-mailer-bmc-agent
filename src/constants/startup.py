"""Constantes del autochequeo de arranque."""

from __future__ import annotations

PREFLIGHT_TIMEOUT_SEC = 60.0


# Reserved TLD (RFC 2606): the check never looks up a real person.
DUMMY_ADDRESS = 'autochequeo@arranque.invalid'


HTTP_BAD_REQUEST = 400
