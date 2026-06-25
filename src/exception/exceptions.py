"""Jerarquía de excepciones del agente IA."""

from __future__ import annotations

from langchain_core.tools import ToolException


class AgentError(Exception):
    """Excepción base del agente IA.

    Toda excepción de dominio del agente debe heredar de esta clase para
    permitir capturarlas selectivamente sin atrapar errores del sistema.
    """


class AgentConfigError(AgentError):
    """Error de configuración del agente.

    Se lanza cuando faltan archivos de configuración, el prompt está vacío,
    o los settings son inválidos.
    """


class ToolAgentError(AgentError, ToolException):
    """Error raised from a LangChain tool that must become ``tool_result`` content.

    Subclasses are caught by ``BaseTool`` when ``handle_tool_error`` is enabled
    and are serialized into the ``ToolMessage`` for the LLM (user-facing
    message via ``str(exc)``).
    """
