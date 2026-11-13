"""Internal LangChain tools for outbound A2A delegation to remote agents."""

from __future__ import annotations

import json
from typing import Annotated

import httpx
from langchain_core.tools import BaseTool
from pydantic import Field

from agent.a2a_peers import A2APeerRegistry, a2a_message_send
from agent.internal_tools.base import ToolSet
from commons.a2a.reply_text import extract_a2a_reply_text
from config import get_logger
from exception import AgentError
from type_defs.models.a2a.a2a import PeerInfo
from type_defs.models.common.json_types import JsonDict

logger = get_logger()


class A2APeerTools(ToolSet):
    """Outbound A2A tools bound to a single :class:`A2APeerRegistry`.

    All registry access and HTTP helpers live on this class; ``get_tools`` instantiates it.
    """

    NO_PEERS_MSG = (
        'No hay agentes remotos A2A configurados. '
        'Define A2A_PEER_URLS: comas y cada entrada `url_base|assistant_id` del peer remoto.'
    )

    # LLM-facing tool descriptions, deliberately separate from each method's own NumPy
    # docstring (see estandar-python.md "Docstring de humanos vs. descripción de tool
    # para el LLM") — StructuredTool.from_function does not fall back to __doc__ the
    # way the bare @tool decorator does, so these must be passed explicitly.
    LIST_REMOTE_AGENTS_DESCRIPTION = (
        'List configured remote A2A agents (index, name, base URL, assistant_id). Use '
        'this first to find a valid peer_index for a2a_send_to_remote.'
    )
    SEND_TO_REMOTE_DESCRIPTION = (
        'Send a user message to a remote agent over A2A. Requires a valid peer_index '
        'from a2a_list_remote_agents. Pass context_id to continue an existing remote '
        'thread, or leave it empty to start a new one.'
    )

    __slots__ = ('_registry',)

    def __init__(self, registry: A2APeerRegistry) -> None:
        self._registry = registry

    @staticmethod
    def get_tools(registry: A2APeerRegistry) -> list[BaseTool]:
        """Return LangChain tools ``a2a_list_remote_agents`` and ``a2a_send_to_remote`` bound to ``registry``."""
        peers = A2APeerTools(registry)
        return [
            peers.build(
                peers.list_remote_agents,
                name='a2a_list_remote_agents',
                description=A2APeerTools.LIST_REMOTE_AGENTS_DESCRIPTION,
            ),
            peers.build(
                peers.send_to_remote,
                name='a2a_send_to_remote',
                description=A2APeerTools.SEND_TO_REMOTE_DESCRIPTION,
            ),
        ]

    async def list_remote_agents(self) -> str:
        """List configured remote A2A agents (index, name, base URL, assistant_id).

        Uses ``A2A_PEER_URLS`` (``url|assistant_id`` per peer). The index is used with
        ``a2a_send_to_remote``.
        """
        res = self._peers_or_error()
        if isinstance(res, str):
            return res
        return self.peer_list_json(res)

    def _peers_or_error(self) -> list[PeerInfo] | str:
        peers = self._registry.list_peers()
        if not peers:
            return self.NO_PEERS_MSG
        return peers

    @staticmethod
    def peer_list_json(peers: list[PeerInfo]) -> str:
        rows = [
            {
                'index': peer.index,
                'name': peer.name,
                'base_url': peer.base_url,
                'assistant_id': peer.assistant_id,
            }
            for peer in peers
        ]
        return json.dumps(rows, indent=2, ensure_ascii=False)

    async def send_to_remote(
        self,
        peer_index: Annotated[
            int,
            Field(description='Peer index from a2a_list_remote_agents (0, 1, …).'),
        ],
        message: Annotated[str, Field(min_length=1, description='User text for the remote agent.')],
        context_id: Annotated[
            str,
            Field(
                description=(
                    'Optional UUID string to continue the same remote thread (A2A contextId); '
                    'leave empty to start a new thread.'
                ),
            ),
        ] = '',
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

    def _resolve_peer_for_send(self, peer_index: int) -> PeerInfo | str:
        res = self._peers_or_error()
        if isinstance(res, str):
            return res
        if peer_index < 0 or peer_index >= len(res):
            return self.invalid_peer_index_message(peer_index)
        return res[peer_index]

    @staticmethod
    def invalid_peer_index_message(peer_index: int) -> str:
        return f'Índice de peer inválido: {peer_index}. Usa a2a_list_remote_agents para ver índices válidos.'

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
            logger.error('a2a_send_to_remote falló peer=%s: %s', peer.index, type(exc).__name__)
            return f'Error al contactar al peer {peer.name}: {exc!s}'

    @staticmethod
    def format_message_send_reply(result: JsonDict) -> str:
        text = extract_a2a_reply_text(result)
        out_id = result.get('id')
        out_ctx = result.get('contextId')
        parts_out = [text] if text else ['(sin texto en la respuesta A2A)']
        if out_ctx or out_id:
            parts_out.append('')
            if out_ctx:
                parts_out.append(f'contextId_devuelto: {out_ctx}')
            if out_id:
                parts_out.append(f'taskId_devuelto: {out_id}')
        return '\n'.join(parts_out)
