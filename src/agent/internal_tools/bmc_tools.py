"""BMC LangChain internal tools for agent-bmc: health check and registry.

The actual Work Order / Incident tool implementations live in
``bmc_work_order_tools.py`` / ``bmc_incident_tools.py`` (split out once this module
grew past the repo's 1000-line-per-module limit). All three modules share one lazy
``BaseToolHandler`` singleton via ``services.bmc.tool_handler.get_shared_handler()`` —
deliberately *not* imported from each other, to avoid a cyclic import between this
aggregator and the two tool modules it registers.
"""

from __future__ import annotations

import logging
import os

from langchain_core.tools import BaseTool

from agent.internal_tools.base import ToolSet
from agent.internal_tools.bmc_incident_tools import IncidentTools
from agent.internal_tools.bmc_staged_files_tools import StagedFilesTools
from agent.internal_tools.bmc_work_order_tools import WorkOrderTools
from exception.mcp import MCPClientError
from services.bmc import tool_handler
from services.bmc.tool_handler import BaseToolHandler
from type_defs.models.bmc.outputs import BaseOutput

logger = logging.getLogger(__name__)


class BmcTools(ToolSet):
    """Health check tool plus the aggregator of every BMC tool group."""

    async def health_check(self) -> str:
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
            logger.warning('bmc_health_check failed: status_code=%s', exc.status_code)
            return BaseToolHandler.failure(exc).model_dump_json()
        logger.info('bmc_health_check successful')
        return BaseOutput(success=True, message='BMC session is healthy.').model_dump_json()

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Return BMC tools when ``BMC_BASE_URL`` is configured; otherwise empty list.

        Returns
        -------
        list[BaseTool]
            All 15 BMC LangChain tools, or ``[]`` when BMC is not configured.
        """
        if not os.environ.get('BMC_BASE_URL'):
            logger.info('BMC_BASE_URL not set — BMC tools disabled')
            return []
        tool_handler.get_shared_handler()
        health = BmcTools()
        tools: list[BaseTool] = [
            health.build(
                health.health_check,
                name='bmc_health_check',
                description=(
                    'Check whether the BMC session is alive and the API is reachable, without '
                    'creating or modifying anything. Call this first if the user reports connection '
                    'errors.'
                ),
            ),
            *WorkOrderTools.get_tools(),
            *IncidentTools.get_tools(),
            *StagedFilesTools.get_tools(),
        ]
        logger.info('BMC tools loaded: %d', len(tools))
        return tools
