"""Internal LangChain tools for outbound A2A delegation to remote agents."""

from __future__ import annotations

import json
from typing import Annotated

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field

from agent.a2a_peers import A2APeerRegistry, a2a_message_send
from commons.a2a_reply_text import extract_a2a_reply_text
from config import get_logger
from exception import AgentError
from type_defs.dicts.a2a import PeerInfo
from type_defs.dicts.json_types import JsonDict

logger = get_logger()


class A2APeerTools:
    """Builds outbound A2A tools closed over a single :class:`A2APeerRegistry`.

    All registry access and HTTP helpers live on this class; the module factory only
    instantiates it and returns ``build_tools()``.
    """

    NO_PEERS_MSG = (
        "No hay agentes remotos A2A configurados. "
        "Define A2A_PEER_URLS: comas y cada entrada `url_base|assistant_id` del peer remoto."
    )

    __slots__ = ("_registry",)

    def __init__(self, registry: A2APeerRegistry) -> None:
        self._registry = registry

    def build_tools(self) -> list[BaseTool]:
        """Return LangChain tools ``a2a_list_remote_agents`` and ``a2a_send_to_remote``."""
        list_doc = (self._list_remote_agents.__doc__ or "").strip()
        send_doc = (self._send_to_remote.__doc__ or "").strip()
        return [
            StructuredTool.from_function(
                coroutine=self._list_remote_agents,
                name="a2a_list_remote_agents",
                description=list_doc,
            ),
            StructuredTool.from_function(
                coroutine=self._send_to_remote,
                name="a2a_send_to_remote",
                description=send_doc,
            ),
        ]

    def _peers_or_error(self) -> list[PeerInfo] | str:
        peers = self._registry.list_peers()
        if not peers:
            return self.NO_PEERS_MSG
        return peers

    @staticmethod
    def peer_list_json(peers: list[PeerInfo]) -> str:
        rows = [
            {
                "index": peer.index,
                "name": peer.name,
                "base_url": peer.base_url,
                "assistant_id": peer.assistant_id,
            }
            for peer in peers
        ]
        return json.dumps(rows, indent=2, ensure_ascii=False)

    @staticmethod
    def invalid_peer_index_message(peer_index: int) -> str:
        return f"Índice de peer inválido: {peer_index}. Usa a2a_list_remote_agents para ver índices válidos."

    def _resolve_peer_for_send(self, peer_index: int) -> PeerInfo | str:
        res = self._peers_or_error()
        if isinstance(res, str):
            return res
        if peer_index < 0 or peer_index >= len(res):
            return self.invalid_peer_index_message(peer_index)
        return res[peer_index]

    @staticmethod
    def format_message_send_reply(result: JsonDict) -> str:
        text = extract_a2a_reply_text(result)
        out_id = result.get("id")
        out_ctx = result.get("contextId")
        parts_out = [text] if text else ["(sin texto en la respuesta A2A)"]
        if out_ctx or out_id:
            parts_out.append("")
            if out_ctx:
                parts_out.append(f"contextId_devuelto: {out_ctx}")
            if out_id:
                parts_out.append(f"taskId_devuelto: {out_id}")
        return "\n".join(parts_out)

    @staticmethod
    async def http_message_send(
        peer: PeerInfo,
        message: str,
        context_id: str | None,
    ) -> JsonDict | str:
        timeout = httpx.Timeout(120.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                return await a2a_message_send(
                    client,
                    base_url=peer.base_url,
                    assistant_id=peer.assistant_id,
                    user_text=message,
                    context_id=context_id,
                )
        except AgentError as exc:
            logger.exception("a2a_send_to_remote falló peer=%s", peer.index)
            return f"Error al contactar al peer {peer.name}: {exc!s}"

    async def _list_remote_agents(self) -> str:
        """List configured remote A2A agents (index, name, base URL, assistant_id).

        Uses ``A2A_PEER_URLS`` (``url|assistant_id`` per peer). The index is used with
        ``a2a_send_to_remote``.
        """
        res = self._peers_or_error()
        if isinstance(res, str):
            return res
        return self.peer_list_json(res)

    async def _send_to_remote(
        self,
        peer_index: Annotated[
            int,
            Field(description="Peer index from a2a_list_remote_agents (0, 1, …)."),
        ],
        message: Annotated[str, Field(min_length=1, description="User text for the remote agent.")],
        context_id: Annotated[
            str,
            Field(
                description=(
                    "Optional UUID string to continue the same remote thread (A2A contextId); "
                    "leave empty to start a new thread."
                ),
            ),
        ] = "",
    ) -> str:
        """Send a user message to a remote agent via JSON-RPC ``message/send`` (A2A).

        Use ``a2a_list_remote_agents`` first to find a valid ``peer_index``.
        """
        peer_or_err = self._resolve_peer_for_send(peer_index)
        if isinstance(peer_or_err, str):
            return peer_or_err
        outcome = await self.http_message_send(
            peer_or_err,
            message,
            context_id.strip() or None,
        )
        if isinstance(outcome, str):
            return outcome
        return self.format_message_send_reply(outcome)


def get_a2a_peer_tools(registry: A2APeerRegistry) -> list[BaseTool]:
    """Return LangChain tools for outbound A2A bound to ``registry``."""
    return A2APeerTools(registry).build_tools()
