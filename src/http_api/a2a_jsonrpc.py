"""Validación y utilidades JSON-RPC A2A inbound ``message/send`` (sin FastAPI).

El servicio HTTP monta ``JSONResponse`` a partir de :class:`A2AInboundRpcFailure`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from config import Settings
from constants.a2a import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    JSONRPC_SERVER_BUSY,
    MSG_AGENT_BUSY,
    MSG_AGENT_UNAVAILABLE,
    MSG_CONTEXT_ID_STRING,
    MSG_CONTEXT_ID_UUID,
    MSG_INVALID_REQUEST,
    MSG_NO_TEXT_IN_PARTS,
    MSG_PARAMS_MESSAGE,
    MSG_PARAMS_OBJECT,
    MSG_PARSE_ERROR,
    MSG_PARTS_EMPTY,
    MSG_SHUTDOWN,
    a2a_jsonrpc_url,
)
from type_defs.enums.domain_literals import RUN_STATUS_SUCCESS
from type_defs.models.a2a.a2a_protocol import (
    A2AInboundMessageSendSuccess,
    A2AInboundTaskStatus,
    AgentForgeAgentCard,
    JsonRpcErrorEnvelope,
    JsonRpcId,
)
from type_defs.models.common.json_types import JsonDict


@dataclass(frozen=True, slots=True)
class A2AInboundRpcFailure:
    """Respuesta de error lista para serializar como JSON + código HTTP."""

    envelope: JsonRpcErrorEnvelope
    http_status: int


@dataclass(frozen=True, slots=True)
class A2AInboundMessageSendRequest:
    """Entrada validada para ejecutar un turno ``message/send``."""

    req_id: JsonRpcId
    user_text: str
    chat_id: UUID | None


class A2AInboundMessageSendProcessor:
    """Parseo y validación estricta de ``message/send``; helpers pequeños y un orquestador."""

    __slots__ = ("_settings",)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def settings(self) -> Settings:
        """Configuración asociada (p. ej. Agent Card y extensiones del mismo endpoint)."""
        return self._settings

    def parse_message_send_from_raw(
        self,
        raw: bytes | None,
    ) -> A2AInboundMessageSendRequest | A2AInboundRpcFailure:
        """Decodifica y valida el cuerpo hasta obtener texto de usuario y ``contextId`` opcional."""
        body_or_fail = self._decode_body_or_failure(raw)
        if isinstance(body_or_fail, A2AInboundRpcFailure):
            return body_or_fail

        failure, req_id, user_text, chat_id = self._validate_message_send_body(body_or_fail)
        if failure is not None:
            return failure
        return A2AInboundMessageSendRequest(req_id=req_id, user_text=user_text, chat_id=chat_id)

    def _validate_message_send_body(
        self,
        body: JsonDict,
    ) -> tuple[A2AInboundRpcFailure | None, JsonRpcId, str, UUID | None]:
        """Ejecuta la cadena de validación; el primer fallo detiene el resto."""
        failure: A2AInboundRpcFailure | None = None
        req_id = self.extract_request_id(body)
        params_d: JsonDict | None = None
        message_d: JsonDict | None = None
        user_text = ""
        chat_id: UUID | None = None

        failure = self._failure_unless_message_send(body, req_id)

        if failure is None:
            params_or_fail = self._require_params_object(body, req_id)
            if isinstance(params_or_fail, A2AInboundRpcFailure):
                failure = params_or_fail
            else:
                params_d = params_or_fail

        if failure is None and params_d is not None:
            message_or_fail = self._require_message_object(params_d, req_id)
            if isinstance(message_or_fail, A2AInboundRpcFailure):
                failure = message_or_fail
            else:
                message_d = message_or_fail

        if failure is None and message_d is not None:
            content_fail, user_text, chat_id = self._validate_message_send_content(message_d, req_id)
            failure = content_fail

        return failure, req_id, user_text, chat_id

    def _validate_message_send_content(
        self,
        message_d: JsonDict,
        req_id: JsonRpcId,
    ) -> tuple[A2AInboundRpcFailure | None, str, UUID | None]:
        """Valida ``parts``, texto de usuario y ``contextId`` opcional."""
        failure: A2AInboundRpcFailure | None = None
        user_text = ""
        chat_id: UUID | None = None

        parts_or_fail = self._require_non_empty_parts_list(message_d, req_id)
        if isinstance(parts_or_fail, A2AInboundRpcFailure):
            failure = parts_or_fail
        else:
            dict_parts = self.coerce_part_dicts(parts_or_fail)
            text_or_fail = self._require_non_empty_user_text(dict_parts, req_id)
            if isinstance(text_or_fail, A2AInboundRpcFailure):
                failure = text_or_fail
            else:
                user_text = text_or_fail
                ctx_or_fail = self._parse_optional_context_uuid(message_d, req_id)
                if isinstance(ctx_or_fail, A2AInboundRpcFailure):
                    failure = ctx_or_fail
                else:
                    chat_id = ctx_or_fail

        return failure, user_text, chat_id

    def failure_graph_unavailable(self, graph: object | None, req_id: JsonRpcId) -> A2AInboundRpcFailure | None:
        if graph is None:
            return self.rpc_failure(req_id, JSONRPC_INTERNAL_ERROR, MSG_AGENT_UNAVAILABLE, 503)
        return None

    def failure_shutdown_requested(self, shutdown_requested: bool, req_id: JsonRpcId) -> A2AInboundRpcFailure | None:
        if shutdown_requested:
            return self.rpc_failure(req_id, JSONRPC_INTERNAL_ERROR, MSG_SHUTDOWN, 503)
        return None

    def failure_agent_busy(self, req_id: JsonRpcId) -> A2AInboundRpcFailure:
        return self.rpc_failure(req_id, JSONRPC_SERVER_BUSY, MSG_AGENT_BUSY, 409)

    @staticmethod
    def rpc_failure(req_id: JsonRpcId, code: int, message: str, http_status: int) -> A2AInboundRpcFailure:
        return A2AInboundRpcFailure(
            envelope=A2AInboundMessageSendProcessor.jsonrpc_error(req_id, code, message),
            http_status=http_status,
        )

    def _decode_body_or_failure(self, raw: bytes | None) -> JsonDict | A2AInboundRpcFailure:
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.rpc_failure(None, JSONRPC_PARSE_ERROR, MSG_PARSE_ERROR, 400)
        if not isinstance(body, dict):
            return self.rpc_failure(None, JSONRPC_INVALID_REQUEST, MSG_INVALID_REQUEST, 400)
        return cast(JsonDict, body)

    @staticmethod
    def extract_request_id(body: JsonDict) -> JsonRpcId:
        return cast(JsonRpcId, body.get("id"))

    def _failure_unless_message_send(self, body: JsonDict, req_id: JsonRpcId) -> A2AInboundRpcFailure | None:
        if body.get("method") != "message/send":
            return self.rpc_failure(
                req_id,
                JSONRPC_METHOD_NOT_FOUND,
                f"Método no soportado: {body.get('method')!r}",
                200,
            )
        return None

    def _require_params_object(self, body: JsonDict, req_id: JsonRpcId) -> JsonDict | A2AInboundRpcFailure:
        params = body.get("params")
        if not isinstance(params, dict):
            return self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_PARAMS_OBJECT, 200)
        return cast(JsonDict, params)

    def _require_message_object(self, params: JsonDict, req_id: JsonRpcId) -> JsonDict | A2AInboundRpcFailure:
        message = params.get("message")
        if not isinstance(message, dict):
            return self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_PARAMS_MESSAGE, 200)
        return cast(JsonDict, message)

    def _require_non_empty_parts_list(
        self,
        message: JsonDict,
        req_id: JsonRpcId,
    ) -> list[object] | A2AInboundRpcFailure:
        parts = message.get("parts")
        if not isinstance(parts, list) or not parts:
            return self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_PARTS_EMPTY, 200)
        return parts

    @staticmethod
    def coerce_part_dicts(parts: list[object]) -> list[JsonDict]:
        return [cast(JsonDict, part) for part in parts if isinstance(part, dict)]

    def _require_non_empty_user_text(
        self,
        dict_parts: list[JsonDict],
        req_id: JsonRpcId,
    ) -> str | A2AInboundRpcFailure:
        user_text = A2AInboundMessageSendProcessor.extract_text_from_parts(dict_parts)
        if not user_text:
            return self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_NO_TEXT_IN_PARTS, 200)
        return user_text

    def _parse_optional_context_uuid(
        self,
        message: JsonDict,
        req_id: JsonRpcId,
    ) -> UUID | None | A2AInboundRpcFailure:
        raw_ctx = message.get("contextId")
        result: UUID | None | A2AInboundRpcFailure = None
        if raw_ctx is None:
            return result
        if not isinstance(raw_ctx, str):
            return self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_CONTEXT_ID_STRING, 200)
        try:
            result = UUID(raw_ctx)
        except ValueError:
            result = self.rpc_failure(req_id, JSONRPC_INVALID_PARAMS, MSG_CONTEXT_ID_UUID, 200)
        return result

    @staticmethod
    def jsonrpc_error(request_id: JsonRpcId, code: int, message: str) -> JsonRpcErrorEnvelope:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    @staticmethod
    def extract_text_from_parts(parts: list[JsonDict]) -> str:
        chunks: list[str] = []
        for part in parts:
            if part.get("kind") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks).strip()

    @staticmethod
    def build_message_send_success(
        *,
        request_id: JsonRpcId,
        reply: str,
        context_id: str,
        task_id: str,
        turn_status: str,
    ) -> A2AInboundMessageSendSuccess:
        status_block: A2AInboundTaskStatus = (
            {"state": "completed"} if turn_status == RUN_STATUS_SUCCESS else {"state": "failed"}
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contextId": context_id,
                "id": task_id,
                "artifacts": [{"parts": [{"kind": "text", "text": reply}]}],
                "status": status_block,
            },
        }

    @staticmethod
    def build_agent_forge_agent_card(base_url: str, settings: Settings) -> AgentForgeAgentCard:
        """Agent Card local (mismo contrato que expone el GET inbound)."""
        aid = settings.effective_a2a_assistant_id
        display = settings.effective_agent_display_name
        return {
            "name": display,
            "description": settings.effective_agent_card_description,
            "protocolVersion": settings.a2a_protocol_version,
            "assistantId": aid,
            "capabilities": {"streaming": False, "pushNotifications": False},
            "skills": [],
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "url": a2a_jsonrpc_url(base_url, aid),
        }
