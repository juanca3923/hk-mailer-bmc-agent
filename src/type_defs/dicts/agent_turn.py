"""Dataclasses que representan el resultado y el contexto de un turno de conversación."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from langchain_core.messages import BaseMessage

from type_defs.dicts.domain_literals import TurnStatus

ErrorKind = Literal["llm_provider", "functional"] | None


@dataclass
class TurnContext:
    """Contexto preparado para la invocación del grafo.

    Agrupa chat_id, run_id y el mensaje nuevo del usuario.
    El historial completo de la conversación lo rehidrata el checkpointer de LangGraph
    a partir de thread_id=chat_id; aquí solo se incluye el HumanMessage del turno actual
    (el mismo texto que envió el usuario).
    """

    chat_id: UUID
    run_id: UUID
    # HumanMessage del turno (texto del usuario sin prefijos)
    messages: list[BaseMessage]


@dataclass
class AgentTurnResult:
    """Resultado de un turno completo de conversación."""

    reply: str
    chat_id: UUID
    run_id: UUID
    status: TurnStatus
    error_kind: ErrorKind = None
