# MCP (Model Context Protocol) en AgentForge

Comportamiento **vigente** en la rama **`agent-base`**: servidores MCP por **Streamable HTTP**, configurados por entorno y abiertos al construir el agente.

---

## Configuración

| Origen | Detalle |
|--------|---------|
| Variable | `MCP_URLS` — URLs separadas por comas |
| Código | [`src/config/settings.py`](../src/config/settings.py) → `mcp_urls`, `normalized_mcp_urls()` |
| Ejemplo | [`.env.example`](../.env.example) (`MCP_URLS=http://localhost:8001/mcp`) |

---

## Ciclo de vida

1. **`build_agent`** ([`src/agent/agent.py`](../src/agent/agent.py)) abre las sesiones MCP dentro de su context manager.
2. **`open_mcp_tools_streamable_http`** ([`src/agent/mcp_tools.py`](../src/agent/mcp_tools.py)) crea una sesión por URL, carga tools con `langchain_mcp_adapters` y las registra en el grafo junto a tools internas (memoria, skills, A2A si aplica).
3. Al salir de `build_agent` (o `stop_agent` en HTTP), las sesiones MCP se cierran.

Implementación actual de transporte:

```text
streamable_http_client(url, terminate_on_close=False)
```

No se pasa `http_client` personalizado de `httpx` → **no hay autenticación por servidor** (Bearer, API key, OAuth) en el código del repo.

---

## Recarga de servidores MCP

### Servicio HTTP (uvicorn sigue en marcha)

1. Actualizar `MCP_URLS` (variable de entorno o `--env-file`).
2. Asegurarse de que el agente **no** está en `DOING_TASK` (o cancelar turnos según operación).
3. `POST /stop` → `POST /start` ([`src/commons/agent_http.py`](../src/commons/agent_http.py)).

Eso cierra el `AsyncExitStack` del agente y vuelve a ejecutar `build_agent` con la nueva lista de URLs. **No** hace falta reiniciar el proceso uvicorn.

### CLI (`uv run agente`)

Tras editar `.env`, el flujo habitual es **detener y volver a arrancar** el proceso del REPL.

---

## Relación con el hilo de conversación

Cambiar MCP **no** borra el historial del checkpointer si mantienes el mismo `chat_id` / `thread_id` en Postgres. Solo cambian las tools disponibles en el grafo a partir del siguiente `start_agent`.

Patrones de memoria y checkpointer: [`docs/MEMORIA.md`](MEMORIA.md).

---

## Limitaciones conocidas (hoy)

| Capacidad | Estado |
|-----------|--------|
| Endpoint `POST /mcp/config` (recarga sin tocar env) | No implementado |
| Auth por servidor (Bearer, `X-Api-Key`, OAuth en `httpx`) | No implementado |
| Recarga MCP con turno en curso sin `stop` | No soportado; con `HTTP_ALLOW_CONCURRENT_TURNS=1` (por defecto) `GET /status = UP` no garantiza que no haya turno en curso — poner `=0` para esa garantía, o usar `POST /stop` para recargar con seguridad |
| Varias credenciales por tenant/usuario en el mismo despliegue | No implementado |

Para extender el código con autorización MCP, la especificación HTTP está en [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization); cualquier cambio deberá documentarse aquí y en [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Archivos relevantes

| Archivo | Rol |
|---------|-----|
| [`src/agent/mcp_tools.py`](../src/agent/mcp_tools.py) | Apertura de sesiones y carga de tools |
| [`src/agent/agent.py`](../src/agent/agent.py) | Integración en `build_agent` |
| [`src/http_api/app.py`](../src/http_api/app.py) | Rutas `/start`, `/stop` |
| [`src/commons/agent_http.py`](../src/commons/agent_http.py) | `start_agent` / `stop_agent` |
