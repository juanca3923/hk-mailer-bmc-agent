"""BMC LangChain internal tools for agent-bmc: health check and registry.

The actual Work Order / Incident tool implementations live in
``bmc_work_order_tools.py`` / ``bmc_incident_tools.py`` (split out once this module
grew past the repo's 1000-line-per-module limit). All three modules share one lazy
``BaseToolHandler`` singleton via ``bmc.libs.tool_handler.get_shared_handler()`` —
deliberately *not* imported from each other, to avoid a cyclic import between this
aggregator and the two tool modules it registers.
"""

from __future__ import annotations

import logging
import os

from langchain_core.tools import BaseTool, tool

from agent.internal_tools.bmc_incident_tools import (
    bmc_add_incident_attachment,
    bmc_add_incident_note,
    bmc_close_incident,
    bmc_create_incident,
    bmc_get_incident,
    bmc_list_incidents_by_email,
)
from agent.internal_tools.bmc_work_order_tools import (
    bmc_add_work_order_attachment,
    bmc_add_work_order_note,
    bmc_close_work_order,
    bmc_create_work_order,
    bmc_get_work_order,
    bmc_list_work_orders_by_email,
    bmc_update_work_order_status,
)
from bmc.exceptions.mcp import MCPClientError
from bmc.libs import tool_handler
from bmc.libs.tool_handler import BaseToolHandler
from bmc.type_defs.outputs import BaseOutput

logger = logging.getLogger(__name__)


@tool(
    description=(
        "Check whether the BMC session is alive and the API is reachable, without "
        "creating or modifying anything. Call this first if the user reports connection "
        "errors."
    )
)
async def bmc_health_check() -> str:
    """Verify BMC JWT session and API reachability with a lightweight authenticated GET.

    Does not create or modify tickets.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` fields.
    """
    handler = tool_handler.get_shared_handler()
    try:
        await handler.client.health_ping()
    except MCPClientError as exc:
        logger.warning("bmc_health_check failed: %s", exc.message)
        return BaseToolHandler.failure(exc).model_dump_json()
    logger.info("bmc_health_check successful")
    return BaseOutput(success=True, message="BMC session is healthy.").model_dump_json()


_ALL_BMC_TOOLS: list[BaseTool] = [
    bmc_health_check,
    bmc_create_work_order,
    bmc_get_work_order,
    bmc_list_work_orders_by_email,
    bmc_add_work_order_note,
    bmc_add_work_order_attachment,
    bmc_update_work_order_status,
    bmc_close_work_order,
    bmc_create_incident,
    bmc_get_incident,
    bmc_list_incidents_by_email,
    bmc_add_incident_note,
    bmc_add_incident_attachment,
    bmc_close_incident,
]


def get_bmc_tools() -> list[BaseTool]:
    """Return BMC tools when ``BMC_BASE_URL`` is configured; otherwise empty list.

    Returns
    -------
    list[BaseTool]
        All 14 BMC LangChain tools, or ``[]`` when BMC is not configured.
    """
    if not os.environ.get("BMC_BASE_URL"):
        logger.info("BMC_BASE_URL not set — BMC tools disabled")
        return []
    tool_handler.get_shared_handler()
    logger.info("BMC tools loaded: %d", len(_ALL_BMC_TOOLS))
    return list(_ALL_BMC_TOOLS)
