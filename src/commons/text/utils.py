"""Utilidades generales del proyecto."""

from __future__ import annotations

from uuid import UUID


def parse_uuid_param(value: str, label: str) -> UUID | str:
    """Parse a UUID string; return an error message string if invalid."""
    try:
        return UUID(value)
    except ValueError:
        return f"{label} inválido: '{value}'"


class TextUtils:
    """Utilidades de manipulación de texto reutilizables en toda la aplicación."""

    @staticmethod
    def truncate(text: str, limit_chars: int) -> str:
        """Trunca un texto a un máximo de caracteres añadiendo indicador de truncado."""
        if len(text) <= limit_chars:
            return text
        return text[:limit_chars] + f"...(truncated {len(text) - limit_chars} chars)"
