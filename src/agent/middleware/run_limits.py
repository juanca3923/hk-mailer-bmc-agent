"""Caps per run so a model cannot repeat tools or loop forever (each extra turn costs tokens and time).

* A tool over its limit is not executed: the model gets "Do not call X again" and has to answer.
* The run limit on model calls ends the run with ``ModelCallLimitExceededError``, so the failure is visible to the
  caller (the runner reports it; over A2A the peer sees an error) instead of the turn hanging.

A limit of ``0`` turns that cap off.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware, ToolCallLimitMiddleware


def build_run_limit_middleware(
    *,
    max_model_calls: int,
    max_tool_calls: int,
    per_tool: dict[str, int],
) -> list[AgentMiddleware[Any, Any, Any]]:
    """Return the middleware that caps model calls, tool calls and calls of chosen tools in one run.

    Parameters
    ----------
    max_model_calls : int
        Most model calls in one run; the run fails with ``ModelCallLimitExceededError`` beyond it (``0`` = no cap).
    max_tool_calls : int
        Most tool calls of any kind in one run; the extra ones are blocked (``0`` = no cap).
    per_tool : dict[str, int]
        Most calls of each named tool in one run (``0`` = no cap for that tool).

    Returns
    -------
    list[AgentMiddleware[Any, Any, Any]]
        Middleware to pass to ``create_agent``; empty when every cap is off.
    """
    middleware: list[AgentMiddleware[Any, Any, Any]] = [
        ToolCallLimitMiddleware(tool_name=name, run_limit=limit, exit_behavior='continue')
        for name, limit in per_tool.items()
        if limit > 0
    ]
    if max_tool_calls > 0:
        middleware.append(ToolCallLimitMiddleware(run_limit=max_tool_calls, exit_behavior='continue'))
    if max_model_calls > 0:
        middleware.append(ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior='error'))
    return middleware
