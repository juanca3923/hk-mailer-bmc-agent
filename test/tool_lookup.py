"""Test helpers to fetch LLM tools by name from the tool classes."""

from __future__ import annotations

import os
from unittest import mock

from langchain_core.tools import BaseTool

from agent.internal_tools.bmc_tools import BmcTools
from services.bmc import tool_handler


def all_bmc_tools() -> list[BaseTool]:
    """Return every BMC tool as ``BmcTools.get_tools`` registers them (without a real BMC handler)."""
    with (
        mock.patch.dict(os.environ, {'BMC_BASE_URL': 'http://bmc.test'}),
        mock.patch.object(tool_handler, 'get_shared_handler', object),
    ):
        return BmcTools.get_tools()


def tool_by_name(tools: list[BaseTool], name: str) -> BaseTool:
    """Return the tool called ``name`` from ``tools``."""
    return next(tool for tool in tools if tool.name == name)


def bmc_tool(name: str) -> BaseTool:
    """Return one BMC tool by its LLM-facing name."""
    return tool_by_name(all_bmc_tools(), name)
