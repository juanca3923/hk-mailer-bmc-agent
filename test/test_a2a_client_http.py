"""Tests del cliente A2A outbound con ``httpx.MockTransport`` (sin red)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from agent.a2a_peers import a2a_message_send, fetch_agent_card

BASE = "http://mock-peer.example"


def _transport_agent_card_ok() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/.well-known/agent-card.json"):
            return httpx.Response(200, json={"name": "RemoteBot", "description": "test peer"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _transport_agent_card_http_error(status: int) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/.well-known/agent-card.json"):
            return httpx.Response(status)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _transport_message_send_ok() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/a2a/" in request.url.path:
            payload: dict[str, Any] = json.loads(request.content.decode())
            assert payload.get("method") == "message/send"
            msg = payload.get("params", {}).get("message", {})
            assert msg.get("role") == "user"
            parts = (msg.get("parts") or [{}])[0]
            assert parts.get("kind") == "text"
            assert parts.get("text") == "hola remoto"
            if "contextId" in msg:
                assert msg["contextId"] == "ctx-uuid"
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "rpc-1",
                    "result": {
                        "artifacts": [{"parts": [{"kind": "text", "text": "  reply  "}]}],
                        "contextId": "ctx-remote",
                    },
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _transport_message_send_jsonrpc_error() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/a2a/" in request.url.path:
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": "x", "error": {"code": -32000, "message": "peer boom"}},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _transport_message_send_no_result() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/a2a/" in request.url.path:
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": "y"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_agent_card_ok() -> None:
    transport = _transport_agent_card_ok()
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        card = await fetch_agent_card(client, BASE, "agent_forge")
    assert card.get("name") == "RemoteBot"
    assert card.get("description") == "test peer"


@pytest.mark.parametrize("status", [404, 500])
@pytest.mark.asyncio
async def test_fetch_agent_card_http_error_returns_empty(status: int) -> None:
    transport = _transport_agent_card_http_error(status)
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        card = await fetch_agent_card(client, BASE, "agent_forge")
    assert card == {}


@pytest.mark.asyncio
async def test_a2a_message_send_ok_without_context() -> None:
    transport = _transport_message_send_ok()
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        result = await a2a_message_send(
            client,
            base_url=BASE,
            assistant_id="agent_forge",
            user_text="hola remoto",
        )
    assert result.get("contextId") == "ctx-remote"
    arts = result.get("artifacts", [])
    assert arts[0]["parts"][0]["text"] == "  reply  "


@pytest.mark.asyncio
async def test_a2a_message_send_ok_with_context_id() -> None:
    transport = _transport_message_send_ok()
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        result = await a2a_message_send(
            client,
            base_url=BASE,
            assistant_id="agent_forge",
            user_text="hola remoto",
            context_id="ctx-uuid",
        )
    assert "artifacts" in result


@pytest.mark.asyncio
async def test_a2a_message_send_jsonrpc_error() -> None:
    transport = _transport_message_send_jsonrpc_error()
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        with pytest.raises(RuntimeError, match="A2A error: peer boom"):
            await a2a_message_send(
                client,
                base_url=BASE,
                assistant_id="agent_forge",
                user_text="x",
            )


@pytest.mark.asyncio
async def test_a2a_message_send_missing_result() -> None:
    transport = _transport_message_send_no_result()
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        with pytest.raises(RuntimeError, match="A2A sin result"):
            await a2a_message_send(
                client,
                base_url=BASE,
                assistant_id="agent_forge",
                user_text="x",
            )


@pytest.mark.asyncio
async def test_a2a_message_send_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/a2a/" in request.url.path:
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await a2a_message_send(
                client,
                base_url=BASE,
                assistant_id="agent_forge",
                user_text="x",
            )
