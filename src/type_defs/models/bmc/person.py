"""Resultados de buscar a una persona en CTM:People."""

from __future__ import annotations

from typing import NamedTuple


class ReporterIdentity(NamedTuple):
    """First/Last Name resolved from a single ``CTM:People`` match."""

    first_name: str
    last_name: str


class PersonCheck(NamedTuple):
    """Result of looking an email up in ``CTM:People`` to decide whether it is a valid origin."""

    exists: bool
    enabled: bool
