"""Constantes del protocolo A2A (JSON-RPC inbound y rutas HTTP relativas)."""

from __future__ import annotations

# JSON-RPC 2.0 — códigos de error estándar y convención del proyecto para ocupación
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603
JSONRPC_SERVER_BUSY = -32000

# Mensajes de error visibles (español)
MSG_PARSE_ERROR = "Parse error"
MSG_INVALID_REQUEST = "Invalid Request"
MSG_PARAMS_OBJECT = "params debe ser un objeto"
MSG_PARAMS_MESSAGE = "params.message es obligatorio"
MSG_PARTS_EMPTY = "parts no puede estar vacío"
MSG_NO_TEXT_IN_PARTS = "No hay texto en parts"
MSG_CONTEXT_ID_STRING = "contextId debe ser string"
MSG_CONTEXT_ID_UUID = "contextId debe ser un UUID"
MSG_AGENT_UNAVAILABLE = "Agente no disponible"
MSG_SHUTDOWN = "Servicio en proceso de parada"
MSG_AGENT_BUSY = "Agente ocupado"

WELL_KNOWN_AGENT_CARD_PATH = "/.well-known/agent-card.json"


def well_known_agent_card_url(base_url: str) -> str:
    """URL absoluta para GET Agent Card (sin query ``assistant_id``)."""
    return f"{base_url.rstrip('/')}{WELL_KNOWN_AGENT_CARD_PATH}"


def a2a_jsonrpc_url(base_url: str, assistant_id: str) -> str:
    """URL absoluta del endpoint JSON-RPC ``POST /a2a/{assistant_id}``."""
    return f"{base_url.rstrip('/')}/a2a/{assistant_id}"
