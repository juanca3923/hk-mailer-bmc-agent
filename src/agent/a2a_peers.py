"""Cliente A2A hacia agentes remotos y registro de peers (Agent Card).

Usado por tools internas y por la CLI para precarga. Los peers vienen de
``Settings.normalized_a2a_peer_configs()`` (env ``A2A_PEER_URLS``: cada entrada
``url_base|assistant_id`` del agente remoto).

El estado del registro vive en una instancia de :class:`A2APeerRegistry`
(creada en ``build_agent`` y enlazada al grafo para introspección desde la CLI).
"""

from __future__ import annotations

import json
import uuid
from typing import cast

import httpx

from config import Settings, get_logger
from constants.a2a import a2a_jsonrpc_url, well_known_agent_card_url
from type_defs.models.a2a.a2a import PeerInfo
from type_defs.models.a2a.a2a_protocol import (
    A2AJsonRpcMessageSendEnvelope,
    A2AOutboundUserMessage,
    A2ATextContentPart,
)
from type_defs.models.common.json_types import JsonDict

logger = get_logger()

GRAPH_ATTR_A2A_REGISTRY = "_agent_forge_a2a_registry"


class A2APeerRegistry:
    """Registro de peers A2A en memoria (una instancia por construcción del grafo)."""

    __slots__ = ("_peers",)

    def __init__(self) -> None:
        self._peers: list[PeerInfo] | None = None

    def clear(self) -> None:
        """Marca el registro como no cargado (p. ej. tests o reutilización explícita)."""
        self._peers = None

    def list_peers(self) -> list[PeerInfo]:
        """Copia de los peers cargados; vacía si no se ha llamado a ``load`` o tras lista vacía."""
        if self._peers is None:
            return []
        return list(self._peers)

    async def load(self, settings: Settings) -> list[PeerInfo]:
        """Descarga Agent Card por cada peer y guarda el resultado en esta instancia."""
        configs = settings.normalized_a2a_peer_configs()
        if not configs:
            self._peers = []
            return []

        peers: list[PeerInfo] = []
        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for idx, (base_url, peer_assistant_id) in enumerate(configs):
                card = await fetch_agent_card(client, base_url, peer_assistant_id)
                name = str(card.get("name", "")).strip() or f"peer_{idx}"
                peers.append(
                    PeerInfo(
                        index=idx,
                        base_url=base_url,
                        assistant_id=peer_assistant_id,
                        name=name,
                        card=card,
                    )
                )

        self._peers = peers
        logger.info("a2a peers cargados: %d", len(peers))
        return peers


def get_a2a_registry_from_graph(graph: object) -> A2APeerRegistry | None:
    """Obtiene el registro A2A enlazado al grafo por ``build_agent``, si existe."""
    reg = getattr(graph, GRAPH_ATTR_A2A_REGISTRY, None)
    return reg if isinstance(reg, A2APeerRegistry) else None


def bind_a2a_registry_to_graph(graph: object, registry: A2APeerRegistry) -> None:
    """Asocia el registro al objeto grafo (usado solo en ``build_agent``)."""
    setattr(graph, GRAPH_ATTR_A2A_REGISTRY, registry)


async def fetch_agent_card(client: httpx.AsyncClient, base_url: str, assistant_id: str) -> JsonDict:
    """GET Agent Card; retorna dict vacío si falla."""
    url = well_known_agent_card_url(base_url)
    try:
        resp = await client.get(url, params={"assistant_id": assistant_id})
        resp.raise_for_status()
        data = resp.json()
        return cast(JsonDict, data) if isinstance(data, dict) else {}
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        logger.warning("a2a Agent Card falló base=%s assistant=%s: %s", base_url, assistant_id, e)
        return {}


async def a2a_message_send(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    assistant_id: str,
    user_text: str,
    context_id: str | None = None,
) -> JsonDict:
    """POST ``message/send``; retorna el objeto ``result`` o lanza."""
    rpc_url = a2a_jsonrpc_url(base_url, assistant_id)
    text_part: A2ATextContentPart = {"kind": "text", "text": user_text}
    message: A2AOutboundUserMessage = {
        "role": "user",
        "parts": [text_part],
        "messageId": str(uuid.uuid4()),
    }
    if context_id:
        message["contextId"] = context_id

    payload: A2AJsonRpcMessageSendEnvelope = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }
    resp = await client.post(rpc_url, json=payload, headers={"Accept": "application/json"})
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        raise RuntimeError("Respuesta A2A no es un objeto JSON")
    body_d = cast(JsonDict, body)
    if "error" in body_d:
        err = body_d["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(f"A2A error: {msg}")
    result = body_d.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("A2A sin result en la respuesta")
    return cast(JsonDict, result)
