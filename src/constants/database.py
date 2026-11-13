"""Constantes de base de datos: longitudes de columna, separadores y SQL fijo."""

from __future__ import annotations

SHORT_STRING_DB_LEN = 20


EVENT_TYPE_DB_LEN = 40


# Separador usado para serializar tuple[str, ...] de namespace a una columna VARCHAR.
# Unit Separator (ASCII 31), improbable en datos normales
NS_SEP = "\x1f"


DELETE_CASCADE_SQL = "all, delete-orphan"
