"""Internal tools for reading Markdown skill guides under `skills/`."""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import BaseTool
from pydantic import Field

from agent.internal_tools.base import ToolSet
from config import get_logger
from config.skill_catalog import read_skill_guide_json_str

logger = get_logger()


class SkillTools(ToolSet):
    """Tool that reads Markdown skill guides."""

    async def get_guide(
        self,
        skill_name: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    'Logical name of the skill (file stem under skills/, e.g. make_report for '
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
        logger.info('skill_get_guide: solicitada skill_name=%r', skill_name)
        return read_skill_guide_json_str(skill_name)

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Return the tools of this group, ready to register on the agent."""
        tools = SkillTools()
        return [
            tools.build(
                tools.get_guide,
                name='skill_get_guide',
                description=(
                    'Read the full content of a skill guide (a Markdown file under skills/) by its '
                    'logical name from the <skills> catalog in the system prompt. Use it when the '
                    "user's task matches a listed skill and you need its detailed procedure — "
                    "never for a stem that isn't in that catalog."
                ),
            ),
        ]
