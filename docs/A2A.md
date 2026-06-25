# A2A (Agent2Agent) en AgentForge

Guía operativa de la integración **A2A** en la rama **`agent-base`**: un solo proceso HTTP (FastAPI) con protocolo embebido y el **mismo grafo** que `POST /chat`.

Detalle técnico (diagramas, inventario de módulos): [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) (sección «A2A»).

---

## Decisión de arquitectura

- **Un proceso**, un `app.state.graph` tras `start_agent` / `build_agent`.
- **Inbound**: rutas A2A en la misma app FastAPI que `/chat` ([`src/http_api/a2a.py`](../src/http_api/a2a.py)).
- **Outbound** (opcional): peers remotos vía `A2A_PEER_URLS` y tools internas en el grafo.
- No se usa un segundo proceso **LangGraph Agent Server** ni `langgraph dev` para A2A en producción de este repo.

---

## Endpoints HTTP (servidor A2A)

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/.well-known/agent-card.json?assistant_id=...` | Agent Card (descubrimiento). El `assistant_id` debe coincidir con el configurado en el servidor. |
| POST | `/a2a/{assistant_id}` | JSON-RPC A2A. Método soportado: **`message/send`**. |

Otros métodos JSON-RPC devuelven error estándar (sin `tasks/get`, sin streaming A2A propio). El turno reutiliza `AgentRunner.run_agent_turn`, el checkpointer (`thread_id` = `chat_id` / `contextId`) y las tablas `chats` / `agent_runs` igual que la API REST.

`POST /chat`, `POST /chat/stream` y A2A comparten el candado de ocupación (`DOING_TASK` → `409` si el agente está en un turno).

Colección de pruebas: [`docs/postman_agente_linux_server.json`](postman_agente_linux_server.json).

---

## Variables de entorno

Ver también [`README.md`](../README.md) y [`.env.example`](../.env.example).

| Variable | Descripción |
|----------|-------------|
| `A2A_ASSISTANT_ID` | Identificador de este agente en Agent Card y en la ruta `/a2a/{assistant_id}`. Si está vacío, se usa `AGENT_SLUG`. |
| `A2A_PROTOCOL_VERSION` | Versión de protocolo declarada en el Agent Card (p. ej. `0.2.6`). |
| `A2A_PEER_URLS` | Lista separada por comas de peers outbound: `url_base\|assistant_id` por entrada (ej. `http://127.0.0.1:9000\|otro_slug`). Entradas mal formadas se omiten al normalizar. |

---

## Outbound (cliente hacia otros agentes)

Si `normalized_a2a_peer_configs()` devuelve al menos un peer al construir el grafo:

1. Se descarga el Agent Card de cada peer ([`src/agent/a2a_peers.py`](../src/agent/a2a_peers.py) — `A2APeerRegistry`).
2. El modelo dispone de las tools `a2a_list_remote_agents` y `a2a_send_to_remote` ([`src/agent/internal_tools/a2a_tools.py`](../src/agent/internal_tools/a2a_tools.py)).

Cambiar `A2A_PEER_URLS` exige **reconstruir el agente** (`POST /stop` + `POST /start` en HTTP, o reiniciar el proceso en CLI).

---

## CLI vs servicio HTTP

| Capa | Servidor A2A inbound | Outbound |
|------|----------------------|----------|
| **HTTP** (`agent-forge-http`) | Sí: `/.well-known/...` y `POST /a2a/...` | Sí, si hay peers en env al arrancar el grafo |
| **CLI** (`uv run agente`) | No expone rutas A2A | Puede **listar** peers cargados al inicio; no levanta servidor |

---

## Tests

Pytest opcional (mocks, sin red): `test/test_a2a_inbound.py`, `test/test_a2a_inbound_processor.py`, `test/test_a2a_peers.py`, `test/test_a2a_client_http.py`. Inventario: [`test/README.md`](../test/README.md).

---

## Limitaciones conocidas (hoy)

- No hay mapeo persistente documentado en BD entre `task_id` remoto A2A y `agent_run_id` local.
- Subagentes supervisor (`linux_ops`, `sql_observability`, etc.) **no** forman parte de esta rama.

---

## Referencias externas

- [Especificación A2A](https://a2a-protocol.org/latest/specification/)
- [Repositorio A2A](https://github.com/a2aproject/A2A)
