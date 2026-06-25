"""Tests unitarios de :class:`commons.a2a_inbound_jsonrpc.A2AInboundMessageSendProcessor`."""

from __future__ import annotations

import json
import uuid
from http import HTTPStatus

import pytest

from commons.a2a_inbound_jsonrpc import (
    A2AInboundMessageSendProcessor,
    A2AInboundMessageSendRequest,
    A2AInboundRpcFailure,
)
from config import Settings

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602


@pytest.fixture()
def settings() -> Settings:
    return Settings.load()


@pytest.fixture()
def proc(settings: Settings) -> A2AInboundMessageSendProcessor:
    return A2AInboundMessageSendProcessor(settings)


def _valid_message_send_body(*, text: str = "hola", context_id: str | None = None) -> bytes:
    msg: dict[str, object] = {
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
        "messageId": str(uuid.uuid4()),
    }
    if context_id is not None:
        msg["contextId"] = context_id
    payload = {
        "jsonrpc": "2.0",
        "id": "rpc-1",
        "method": "message/send",
        "params": {"message": msg},
    }
    return json.dumps(payload).encode("utf-8")


def test_parse_invalid_json_returns_400(proc: A2AInboundMessageSendProcessor) -> None:
    out = proc.parse_message_send_from_raw(b"{no json")
    assert isinstance(out, A2AInboundRpcFailure)
    assert out.http_status == HTTPStatus.BAD_REQUEST
    assert out.envelope["error"]["code"] == JSONRPC_PARSE_ERROR


def test_parse_non_dict_body_returns_400(proc: A2AInboundMessageSendProcessor) -> None:
    out = proc.parse_message_send_from_raw(json.dumps(["a"]).encode())
    assert isinstance(out, A2AInboundRpcFailure)
    assert out.http_status == HTTPStatus.BAD_REQUEST
    assert out.envelope["error"]["code"] == JSONRPC_INVALID_REQUEST


def test_wrong_method_returns_200_with_error(proc: A2AInboundMessageSendProcessor) -> None:
    raw = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {}},
    ).encode()
    out = proc.parse_message_send_from_raw(raw)
    assert isinstance(out, A2AInboundRpcFailure)
    assert out.http_status == HTTPStatus.OK
    assert out.envelope["error"]["code"] == JSONRPC_METHOD_NOT_FOUND


def test_params_not_object(proc: A2AInboundMessageSendProcessor) -> None:
    raw = json.dumps(
        {"jsonrpc": "2.0", "id": "x", "method": "message/send", "params": []},
    ).encode()
    out = proc.parse_message_send_from_raw(raw)
    assert isinstance(out, A2AInboundRpcFailure)
    assert out.envelope["error"]["code"] == JSONRPC_INVALID_PARAMS


def test_message_send_ok(proc: A2AInboundMessageSendProcessor) -> None:
    out = proc.parse_message_send_from_raw(_valid_message_send_body())
    assert isinstance(out, A2AInboundMessageSendRequest)
    assert out.user_text == "hola"
    assert out.chat_id is None
    assert out.req_id == "rpc-1"


def test_context_id_uuid_ok(proc: A2AInboundMessageSendProcessor) -> None:
    cid = str(uuid.uuid4())
    out = proc.parse_message_send_from_raw(_valid_message_send_body(context_id=cid))
    assert isinstance(out, A2AInboundMessageSendRequest)
    assert out.chat_id == uuid.UUID(cid)


def test_context_id_invalid_string(proc: A2AInboundMessageSendProcessor) -> None:
    out = proc.parse_message_send_from_raw(_valid_message_send_body(context_id="not-a-uuid"))
    assert isinstance(out, A2AInboundRpcFailure)
    assert out.envelope["error"]["code"] == JSONRPC_INVALID_PARAMS


def test_jsonrpc_error_static() -> None:
    env = A2AInboundMessageSendProcessor.jsonrpc_error(None, -1, "x")
    assert env["jsonrpc"] == "2.0"
    assert env["error"]["message"] == "x"
