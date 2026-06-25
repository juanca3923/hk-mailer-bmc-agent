"""MCP tools usando Streamable HTTP."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from config import get_logger

_logger = get_logger()


@asynccontextmanager
async def open_mcp_tools_streamable_http(urls: list[str]) -> AsyncIterator[list[BaseTool]]:
    """
    Abre 1..N sesiones MCP por Streamable HTTP y expone todas sus tools.

    Mantiene las sesiones abiertas mientras dure el contexto, para que las tools funcionen.
    """
    tools: list[BaseTool] = []
    async with AsyncExitStack() as stack:
        for url in urls:
            read, write, _ = await stack.enter_async_context(streamable_http_client(url, terminate_on_close=False))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            server_tools = await load_mcp_tools(session)
            for tool in server_tools:
                _logger.info("Tool: %s", tool.name)
            tools.extend(server_tools)

        yield tools
