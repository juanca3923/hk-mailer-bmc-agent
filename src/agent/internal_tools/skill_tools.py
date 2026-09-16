"""Internal tools for reading Markdown skill guides under `skills/`."""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from config import get_logger
from config.skill_catalog import read_skill_guide_json_str

logger = get_logger()


@tool
async def skill_get_guide(
    skill_name: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Logical name of the skill (file stem under skills/, e.g. make_report for "
                'make_report.md). Do not include path separators or "..".'
            ),
        ),
    ],
) -> str:
    """Read the full content of a skill guide (a Markdown file under `skills/`).

    Use it when the user's task matches a skill listed in the ``<skills>`` block of
    the system prompt and you need its detailed procedure. Returns a JSON with
    ``ok``, ``content`` and metadata, or ``ok: false`` and ``error`` on failure.
    """
    logger.info("skill_get_guide: solicitada skill_name=%r", skill_name)
    return read_skill_guide_json_str(skill_name)


def get_skill_tools() -> list[BaseTool]:
    """Return the internal skill tools to register on the graph."""
    return [skill_get_guide]
