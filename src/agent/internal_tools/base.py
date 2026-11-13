"""Base for the classes that expose tools to the LLM: explicit descriptions and visible errors."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, ValidationError

from agent.tool_error_policy import format_validation_error
from config import get_logger

logger = get_logger()

MAX_ERROR_CHARS = 200


def _unexpected_message(name: str, exc: Exception) -> str:
    """Short message for the LLM: tool, exception type and trimmed text (no traceback, no payload)."""
    detail = str(exc)[:MAX_ERROR_CHARS]
    return f'{name} falló: {type(exc).__name__}: {detail}' if detail else f'{name} falló: {type(exc).__name__}'


def _as_tool_exception(name: str, exc: Exception) -> ToolException:
    """Turn an exception raised inside a tool body into one the LLM can read."""
    if isinstance(exc, ValidationError):
        return ToolException(format_validation_error(exc))
    logger.exception('tool %s: unexpected error type=%s', name, type(exc).__name__)
    return ToolException(_unexpected_message(name, exc))


def _guard(function: Callable[..., Any], name: str) -> Callable[..., Any]:
    """Wrap a tool function so any error but a ``ToolException`` reaches the LLM as one."""
    if inspect.iscoroutinefunction(function):

        @functools.wraps(function)
        async def async_guarded(*args: Any, **kwargs: Any) -> Any:
            try:
                return await function(*args, **kwargs)
            except ToolException:
                raise
            # Any failure of a tool must reach the LLM as a ToolException (the policy shows it instead of
            # aborting the turn); the traceback goes to the log.
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise _as_tool_exception(name, exc) from exc

        return async_guarded

    @functools.wraps(function)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except ToolException:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise _as_tool_exception(name, exc) from exc

    return guarded


class ToolSet:
    """Base of the classes that group tools; each one exposes ``get_tools`` as a static method."""

    @staticmethod
    def build(
        function: Callable[..., Any],
        *,
        name: str,
        description: str,
        args_schema: type[BaseModel] | None = None,
    ) -> StructuredTool:
        """Create a tool from a function or coroutine with an explicit description.

        Parameters
        ----------
        function : Callable[..., Any]
            Sync function or coroutine function with the tool logic (a bound method is fine).
        name : str
            Tool name the LLM calls.
        description : str
            What the tool does and when to use it; never inferred from the docstring.
        args_schema : type[BaseModel] | None, optional
            Explicit argument schema; by default it is inferred from the signature.

        Returns
        -------
        StructuredTool
            The tool; any failure inside it reaches the LLM as a ``ToolException``.

        Raises
        ------
        ValueError
            When ``description`` is empty.
        """
        if not description.strip():
            raise ValueError(f'La tool {name} necesita una description explícita')
        if inspect.iscoroutinefunction(function):
            tool = StructuredTool.from_function(
                coroutine=function, name=name, description=description.strip(), args_schema=args_schema
            )
        else:
            tool = StructuredTool.from_function(
                func=function, name=name, description=description.strip(), args_schema=args_schema
            )
        # The schema was inferred from the original signature; only the callable is guarded.
        if tool.coroutine is not None:
            tool.coroutine = _guard(tool.coroutine, name)
        if tool.func is not None:
            tool.func = _guard(tool.func, name)
        return tool
