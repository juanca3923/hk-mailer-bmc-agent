"""Tools internas para leer guías/skills Markdown bajo `skills/`."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from config import get_logger
from config.skill_catalog import read_skill_guide_json_str

logger = get_logger()


@tool
async def skill_get_guide(skill_name: str) -> str:
    """Lee el contenido completo de una guía skill (archivo Markdown bajo `skills/`).

    Args:
        skill_name: Nombre lógico de la skill (stem del archivo, ej. `make_report` para
            `make_report.md`). No incluyas rutas ni `..`.

    Retorna JSON con `ok`, `content` y metadatos, o `ok: false` y `error` si falla.
    Úsala cuando la tarea del usuario se alinee con una skill listada en el bloque
    ``<skills>`` del system prompt y necesites el procedimiento detallado.
    """
    logger.info("skill_get_guide: solicitada skill_name=%r", skill_name)
    return read_skill_guide_json_str(skill_name)


def get_skill_tools() -> list[BaseTool]:
    """Retorna las tools internas de skills para registrarlas en el grafo."""
    return [skill_get_guide]
