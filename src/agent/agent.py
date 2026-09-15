"""BMC agent LangGraph build context manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.tools import BaseTool

from agent.a2a_peers import A2APeerRegistry, bind_a2a_registry_to_graph
from agent.internal_tools import (
    get_a2a_peer_tools,
    get_bmc_tools,
    get_datetime_tools,
    get_memory_tools,
    get_skill_tools,
)
from agent.llm import build_llm
from agent.mcp_tools import open_mcp_tools_streamable_http
from agent.prompts import load_system_prompt_for_settings
from agent.tool_error_policy import configure_tool_error_handling
from commons.langfuse_tracing import ensure_langfuse_tracing_client
from config import Settings, get_logger
from database.checkpointer import CheckpointerManager
from database.store import AgentPostgresStore

logger = get_logger()


@asynccontextmanager
async def build_agent(settings: Settings) -> AsyncIterator[object]:
    """Build a LangGraph agent with persistent checkpointer, store and BMC tools.

    Lifecycle
    ---------
    1. Optionally start ``BmcConnectionManager`` when ``BMC_BASE_URL`` is set (fail-fast).
    2. Open asyncpg pool and configure ``AsyncPostgresSaver`` (checkpointer).
    3. Create ``AgentPostgresStore`` (cross-thread persistent store).
    4. Load internal tools: memory, skills, datetime, BMC (if configured), A2A peers (if configured).
    5. Open MCP sessions (Streamable HTTP) for any extra ``MCP_URLS``.
    6. Compile the LangGraph with checkpointer + store.
    7. On exit: stop BMC connection manager and close pool / MCP sessions.

    Notes
    -----
    The checkpointer manages conversation continuity per ``thread_id`` (= ``chat_id``).
    The store allows the agent to persist cross-chat data (e.g. memory facts).
    BMC tools are loaded only when ``BMC_BASE_URL`` env var is present.
    """
    ensure_langfuse_tracing_client(settings)
    system_prompt_text = load_system_prompt_for_settings(settings)
    llm = build_llm(settings)

    # BMC session lifecycle — conditional on configuration
    bmc_manager = None
    import os
    if os.environ.get("BMC_BASE_URL"):
        from bmc.config.settings import BmcSettings
        from bmc.libs.connection_manager import BmcConnectionManager
        from bmc.exceptions.mcp import MCPLoginError

        bmc_manager = BmcConnectionManager.instance(BmcSettings())
        try:
            await bmc_manager.start()
            logger.info("BMC session started")
        except MCPLoginError:
            logger.error("BMC login failed at startup; BMC tools will be unavailable")
            bmc_manager = None

    try:
        bmc_tools = get_bmc_tools()
        internal_tools = get_memory_tools() + get_skill_tools() + get_datetime_tools() + bmc_tools
        logger.info("tools internas cargadas: %d (bmc: %d)", len(internal_tools), len(bmc_tools))

        # W0135 false positive: @asynccontextmanager + async-with anidados; el cierre se hace al salir del generador.
        # pylint: disable=contextmanager-generator-missing-cleanup
        async with CheckpointerManager.build(settings) as checkpointer:
            store = AgentPostgresStore()
            logger.info("store postgres inicializado")
            logger.info("conectado ha: %s", settings.llm_provider)
            async with open_mcp_tools_streamable_http(settings.normalized_mcp_urls()) as mcp_tools:
                logger.info("tools MCP cargadas: %d", len(mcp_tools))

                peer_cfgs = settings.normalized_a2a_peer_configs()
                a2a_registry_for_graph: A2APeerRegistry | None = None
                a2a_tools: list[BaseTool] = []
                if peer_cfgs:
                    a2a_registry_for_graph = A2APeerRegistry()
                    await a2a_registry_for_graph.load(settings)
                    a2a_tools = get_a2a_peer_tools(a2a_registry_for_graph)
                    logger.info("tools A2A remotas: %d", len(a2a_tools))

                all_tools = internal_tools + list(mcp_tools) + a2a_tools
                configure_tool_error_handling(all_tools)
                logger.info("system prompt: <system_prompt>\n%s\n</system_prompt>", system_prompt_text)
                logger.info(
                    "total tools disponibles: <tools>\n%s\n</tools>",
                    "\n".join([tool.name for tool in all_tools]),
                )

                graph = create_agent(
                    llm,
                    all_tools,
                    system_prompt=system_prompt_text,
                    checkpointer=checkpointer,
                    store=store,
                )
                if a2a_registry_for_graph is not None:
                    bind_a2a_registry_to_graph(graph, a2a_registry_for_graph)
                logger.debug(
                    "grafo compilado con checkpointer=%s store=%s",
                    type(checkpointer).__name__,
                    type(store).__name__,
                )
                yield graph
    finally:
        if bmc_manager is not None:
            await bmc_manager.stop()
            logger.info("BMC session stopped")
