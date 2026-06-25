"""Central policy: tool failures become ToolMessage content instead of aborting the turn."""

from __future__ import annotations

from langchain_core.tools import BaseTool


def configure_tool_error_handling(tools: list[BaseTool]) -> None:
    """Enable LangChain tool error handling on every graph tool.

    Tool code should raise subclasses of ``ToolAgentError``, which inherit
    ``ToolException``. With ``handle_tool_error=True``, LangChain serializes
    ``str(exc)`` into the tool result so the LLM can continue the turn and the
    checkpointer keeps paired ``tool_use`` / ``tool_result`` blocks.

    Parameters
    ----------
    tools
        All tools passed to ``create_agent`` (internal, MCP, A2A).
    """
    for tool in tools:
        tool.handle_tool_error = True
        tool.handle_validation_error = True
