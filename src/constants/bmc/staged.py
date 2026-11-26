"""Constantes de los archivos de adjuntos de la carpeta compartida."""

from __future__ import annotations

import re

STAGING_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')


MANIFEST_FILE_NAME = 'manifest.json'


# Same default as the mailer's TICKET_FILES_ALLOWED_EXTENSIONS (the variable is shared by both agents).
DEFAULT_ALLOWED_EXTENSIONS = 'pdf,png,jpg,jpeg,gif,bmp,doc,docx,xls,xlsx,csv,txt'


# The original email the mailer always stages; it is not a user attachment, so it is never filtered.
ALWAYS_ALLOWED_EXTENSIONS = frozenset({'eml'})


BYTES_PER_KB = 1024


BYTES_PER_MB = 1024 * 1024
