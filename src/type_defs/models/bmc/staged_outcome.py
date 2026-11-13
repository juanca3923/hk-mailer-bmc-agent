"""Resultado acumulado de subir los archivos de una carpeta compartida."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StagedOutcome:
    """Accumulated result of one staging folder."""

    attached: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    sizes: dict[str, int] = field(default_factory=dict)
