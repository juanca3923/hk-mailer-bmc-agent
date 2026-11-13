"""Constantes de los archivos de adjuntos de la carpeta compartida."""

from __future__ import annotations

import re

STAGING_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')


MANIFEST_FILE_NAME = 'manifest.json'


BYTES_PER_KB = 1024


BYTES_PER_MB = 1024 * 1024
