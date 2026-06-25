"""Tipos estructurados para JSON-RPC A2A (inbound AgentForge y outbound hacia peers).

``JsonDict`` (`type_defs.dicts.json_types`) cubre JSON de forma desconocida; aquí se
definen TypedDict donde el contrato A2A / JSON-RPC es estable.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# JSON-RPC 2.0: ``id`` puede ser string, número o ``null`` (omitido se representa como None).
JsonRpcId = str | int | float | None


class JsonRpcErrorData(TypedDict):
    """``error.data`` en la respuesta de error de JSON-RPC."""

    code: int
    message: str


class JsonRpcErrorEnvelope(TypedDict):
    """Envío JSON-RPC de error."""

    jsonrpc: Literal["2.0"]
    id: JsonRpcId
    error: JsonRpcErrorData


class AgentCardCapabilities(TypedDict):
    """``capabilities`` en Agent Card (inbound)."""

    streaming: bool
    pushNotifications: bool


class AgentForgeAgentCard(TypedDict):
    """Agent Card devuelto por este servidor (inbound)."""

    name: str
    description: str
    protocolVersion: str
    assistantId: str
    capabilities: AgentCardCapabilities
    skills: list[str]
    defaultInputModes: list[str]
    defaultOutputModes: list[str]
    url: str


class A2ATextContentPart(TypedDict):
    """``parts`` en ``message/send`` hacia un peer remoto."""

    kind: Literal["text"]
    text: str


class A2AOutboundUserMessageBase(TypedDict):
    """Campos obligatorios de ``params.message`` (outbound)."""

    role: Literal["user"]
    parts: list[A2ATextContentPart]
    messageId: str


class A2AOutboundUserMessage(A2AOutboundUserMessageBase, total=False):
    """``params.message`` en ``message/send`` hacia un peer remoto."""

    contextId: str


class A2AJsonRpcMessageSendParams(TypedDict):
    """``params`` en ``message/send`` hacia un peer remoto."""

    message: A2AOutboundUserMessage


class A2AJsonRpcMessageSendEnvelope(TypedDict):
    """Envío JSON-RPC ``message/send`` hacia un peer remoto."""

    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send"]
    params: A2AJsonRpcMessageSendParams


class A2AInboundTaskStatus(TypedDict):
    """``status`` en la respuesta exitosa de ``message/send`` (inbound)."""

    state: Literal["completed", "failed"]


class A2AInboundArtifactTextPart(TypedDict):
    """``parts`` en la respuesta exitosa de ``message/send`` (inbound)."""

    kind: Literal["text"]
    text: str


class A2AInboundArtifact(TypedDict):
    """``artifacts`` en la respuesta exitosa de ``message/send`` (inbound)."""

    parts: list[A2AInboundArtifactTextPart]


class A2AInboundMessageSendResultBody(TypedDict):
    """Objeto ``result`` en la respuesta exitosa de ``message/send`` (inbound)."""

    contextId: str
    id: str
    artifacts: list[A2AInboundArtifact]
    status: A2AInboundTaskStatus


class A2AInboundMessageSendSuccess(TypedDict):
    """Objeto ``result`` en la respuesta exitosa de ``message/send`` (inbound)."""

    jsonrpc: Literal["2.0"]
    id: JsonRpcId
    result: A2AInboundMessageSendResultBody
