"""TypedDicts para el catálogo de skills locales."""

from __future__ import annotations

from typing import TypedDict


class SkillCatalogEntry(TypedDict):
    """Entrada del catálogo de skills inyectado en el system prompt.

    Attributes
    ----------
    stem : str
        Nombre lógico de la skill (stem del archivo o nombre de carpeta).
    description : str
        Descripción breve en una sola línea para el bloque ``<skills>``.
    """

    stem: str
    description: str
