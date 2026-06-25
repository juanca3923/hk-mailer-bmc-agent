"""Excepciones de dominio del agente IA — re-exporta desde exception.exceptions."""

from exception.exceptions import AgentConfigError, AgentError, ToolAgentError

__all__ = ["AgentConfigError", "AgentError", "ToolAgentError"]
