"""Central policy: tool failures become ToolMessage content instead of aborting the turn."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import ValidationError
from pydantic.v1 import ValidationError as ValidationErrorV1


def format_validation_error(exc: ValidationError | ValidationErrorV1) -> str:
    """Describe invalid tool arguments for the LLM: field and reason, never the received value.

    Parameters
    ----------
    exc : ValidationError
        Validation error raised for the tool arguments or by a model built inside the tool.

    Returns
    -------
    str
        One line such as ``Argumentos inválidos: text: Field required``.
    """
    errors: list[Mapping[str, Any]] = (
        list(exc.errors(include_input=False, include_url=False, include_context=False))
        if isinstance(exc, ValidationError)
        else list(exc.errors())
    )
    fields = '; '.join(
        f'{".".join(str(part) for part in error["loc"]) or "argumentos"}: {error["msg"]}' for error in errors
    )
    return f'Argumentos inválidos: {fields}'


def configure_tool_error_handling(tools: list[BaseTool]) -> None:
    """Make every tool failure readable by the LLM instead of aborting the turn.

    ``ToolException`` (``ToolAgentError`` and subclasses such as ``GraphMailboxError``) becomes the content
    of the ``ToolMessage`` through ``handle_tool_error``; invalid arguments are described field by field
    (not the generic LangChain text). Tools built with ``ToolSet.build`` also convert unexpected exceptions
    into a ``ToolException``.

    Parameters
    ----------
    tools
        All tools passed to ``create_agent`` (internal, MCP, A2A).
    """
    for tool in tools:
        tool.handle_tool_error = True
        tool.handle_validation_error = format_validation_error
