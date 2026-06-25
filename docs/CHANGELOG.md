# Changelog

Registro de cambios **relevantes** del proyecto **agent-bmc**.

---

## 2026-06-25 — feat: creación del agente BMC (agent-bmc)

- **Nuevo proyecto** basado en `agent_forge`: agente LangGraph para gestión de incidentes y
  órdenes de trabajo en BMC Helix ARUS.
- **`src/bmc/`**: paquete BMC completo copiado de `bmc-mcp` (config, libs, type_defs); imports
  actualizados de `src.*` → `bmc.*`.
- **`src/bmc/libs/tool_handler.py`**: `BaseToolHandler` con write guard, TOON encoder y carga de adjuntos.
- **`src/agent/internal_tools/bmc_tools.py`**: 12 LangChain `@tool` functions que envuelven BMC Helix
  AR REST (health, 6 WO, 5 incident). Handler lazy inicializado; `get_bmc_tools()` retorna lista
  vacía si `BMC_BASE_URL` no está configurado.
- **`src/agent/agent.py`**: `build_agent()` inicia `BmcConnectionManager` condicionalmente (fail-fast
  en login fallido); BMC tools incluidas en `all_tools`; stop garantizado en el bloque `finally`.
- **`pyproject.toml`**: nombre `agent-bmc`, dependencia `toon-formatter==1.0.1`, paquete `src/bmc`,
  entry point `agent-bmc-http`.
- **`system.promt.md`**: system prompt específico para gestión de tickets BMC ARUS.
- **`.env.example`**: sección BMC con `BMC_BASE_URL`, `BMC_USERNAME`, `BMC_PASSWORD`, `BMC_ALLOW_WRITE`.
- **`~/.ssh/config`**: entrada explícita para `ssh.dev.azure.com` (Azure DevOps) preservando GitHub.

---

## Historial previo (agent_forge) A partir de 2026-04-19 las entradas **omitienen cambios meramente documentales** (solo enlaces o redacción sin impacto en código ni operación); el detalle fino sigue disponible en el historial de **git**.

---

## 2026-05-21 — sync: mejoras desde mailer_agent (sin correo Graph)

- **`exception/exceptions.py`**: `ToolAgentError(AgentError, ToolException)` para errores de tools que deben serializarse en el `ToolMessage`.
- **`agent/tool_error_policy.py`**: `configure_tool_error_handling` activa `handle_tool_error` en todas las tools del grafo (internas, MCP, A2A).
- **`agent/agent.py`**: aplica la política antes de `create_agent`; **`agent/mcp_tools.py`**: deja de configurar errores por tool (centralizado).
- **`agent/llm.py`**: prompt caching en OpenAI (`prompt_cache_key` por `AGENT_SLUG`) y Anthropic (`cache_control` efímero).
- **`services/agent_runs_service.py`**: lecturas `get_active_run`, `list_recent_runs`, `get_run_with_events` (sustituyen `memory_queries.py`).
- **`commons/serializers/memory_serializer.py`**: `MemorySerializer` movido desde `internal_tools/`; **`commons/utils.py`**: `parse_uuid_param`.
- **Docker**: usuario `appuser`, directorio `/app/logs` con permisos; **`Dockerfile.dev`**: `watchfiles` vía `sh -c` con `${HTTP_HOST}` / `${HTTP_PORT}`.
- **Test**: `test/test_tool_error_handling.py`.

## 2026-05-19 — fix: imágenes Docker incluyen `skills/` y `base.prompt.md`

- **`Dockerfile`** y **`Dockerfile.dev`**: `COPY skills` en `/app/skills` (sin `skills/example/`); `COPY base.prompt.md` para políticas de memoria y skills en runtime.
- **`.dockerignore`**: excluye `skills/example` del contexto de build.
- **`base.prompt.md`**: regla crítica — `skill_get_guide` solo resuelve stems listados en `<skills>`; prohibido adivinar nombres.

---

## 2026-05-19 — docs: guías A2A y MCP (sin documentos de plan)

- **Eliminados** (roadmap / comparativas obsoletas): `docs/A2A_LANGCHAIN_Y_PLAN_MULTIAGENTE.md`, `docs/A2A_TRES_ENFOQUES_IMPLEMENTACION.md`, `docs/MCP_HTTP_RECARGA_Y_AUTENTICACION.md`.
- **Nuevos**: `docs/A2A.md` (A2A embebido en FastAPI, inbound/outbound vigente), `docs/MCP.md` (MCP por env, recarga vía `/stop` + `/start`).
- **Actualizados**: `docs/ARCHITECTURE.md`, `README.md`, `docs/skills-implementation.md` (enlaces y `create_agent` en tabla A2A).

---

## 2026-05-19 — feat: catálogo de skills en system prompt (`<skills>`)

- **`src/config/skill_catalog.py`**: descubrimiento de `skills/*.md` y `skills/<dir>/SKILL.md`; bloque XML `stem => descripción` (frontmatter o primer `#`); lectura dual en `skill_get_guide`; eliminada inyección por turno en el mensaje del usuario.
- **`src/agent/prompts.py`**: `finalize_system_prompt` añade el catálogo al final solo si hay guías (sin etiquetas vacías).
- **`src/commons/runner.py`**: el `HumanMessage` del turno usa el mensaje del usuario tal cual.
- **`test/test_skill_catalog.py`**: tests de catálogo, XML y resolución de rutas.
- **Documentación**: `docs/skills-implementation.md` (sección `agent-base`), `docs/ARCHITECTURE.md`, `README.md`, `docs/MEMORIA.md`, `test/README.md`.

---

## 2026-05-19 — refactor: rama `agent-base` con `create_agent` + A2A (sin `deepagents`)

Creación de dos líneas paralelas de desarrollo a partir de `initial-commit` (HEAD de la rama del mismo nombre):

- **Tag `deep-agent-v1`** y **rama `deep-agent-base`**: snapshot del estado actual con `create_deep_agent`, `FilesystemBackend` y skills vía `SKILL.md`. Rama de trabajo para evolucionar la línea Deep Agent.
- **Rama `agent-base`**: implementación equivalente con `create_agent` de LangChain estándar. No tiene dependencia de `deepagents`. Diferencias respecto a `deep-agent-base`:
  - `src/agent/agent.py`: usa `create_agent`; sin `FilesystemBackend` ni `_repo_root()`.
  - `src/config/skill_catalog.py` + `src/agent/internal_tools/skill_tools.py`: restaurados; tool `skill_get_guide` (catálogo inicialmente por turno en el mensaje del usuario; *sustituido por bloque `<skills>` en system prompt — ver entrada **feat** anterior en este changelog*).
  - `src/commons/runner.py`: en el primer commit de la rama, `prepare_turn` antepuso la lista de skills al mensaje al LLM (*mismo sustituto que arriba*).
  - `pyproject.toml` / `uv.lock`: `deepagents==0.5.3` eliminado junto a sus dependencias exclusivas (`langchain-google-genai`, `google-genai`, `google-auth`, `filetype`, `wcmatch`, `bracex`).
  - A2A (inbound + outbound), Langfuse, multi-proveedor LLM, compose y toda la infra de `initial-commit` son idénticos en ambas ramas.

---

## 2026-05-15 — docs: `LANGFUSE_PROMPT_LABEL` en ejemplo y documentación

- **`.env.example`**: documenta `LANGFUSE_PROMPT_LABEL` (etiqueta Langfuse; por defecto `latest` en la app) y aclara requisitos junto a `LANGFUSE_PROMPT_NAME`.
- **`README.md`**: sección de configuración y troubleshooting Langfuse alineadas a las cuatro variables de trazas y a la etiqueta en la descarga del prompt.
- **`docs/ARCHITECTURE.md`** / **`docs/skills-implementation.md`**: `Settings`, `prompts.py` y cadena de carga del system prompt con `LANGFUSE_PROMPT_LABEL`.

---

- **compose.yml**: variables explícitas en `environment` desde cualquier `--env-file`; `POSTGRES_DB` como `db_${AGENT_SLUG}`; Postgres publicado en 5432; sin `env_file`.
- **README.md** / **`.env.example`**: uso de `--env-file` con distintos perfiles y notas sobre `DATABASE_URL` con host `postgres`.

---

## 2026-05-14 — A2A outbound: `A2A_PEER_URLS` exige `url|agent_id`

- **config/settings.py**: elimina `A2A_REMOTE_ASSISTANT_ID`; `normalized_a2a_peer_configs()` solo incluye segmentos `url_base|assistant_id` (ambas partes no vacías); el resto se omite (log WARNING).
- **agent**: mensajes en `cli.py`, `internal_tools/a2a_tools.py`; docstring en `a2a_peers.py`.
- **Documentación**: README, `docs/ARCHITECTURE.md`, `docs/A2A_TRES_ENFOQUES_IMPLEMENTACION.md`, `docs/A2A_LANGCHAIN_Y_PLAN_MULTIAGENTE.md`, `.env.example`; test `test/test_settings_multiinstance.py` (`test_normalized_a2a_peer_configs_requires_url_pipe_agent_id`); `test/conftest.py` (env mínimo para importar `config` en pytest).

---

## 2026-05-14 — chore: versiones exactas en `pyproject.toml`

- **pyproject.toml**: dependencias de runtime y grupo `dev` fijadas con `==` alineadas al `uv.lock` vigente; las actualizaciones de paquetes pasan a ser explícitas (`uv lock` / revisión del lock).

---

## 2026-05-14 — chore: Docker y CI alineados con `uv.lock`

- **Dockerfile** / **Dockerfile.dev**: copian `uv.lock` y ejecutan `uv sync --frozen` para no re-resolver el árbol sin el lock.
- **README.md**: nota de reproducibilidad en CI; descripción Docker actualizada.
- **.dockerignore**: comentario del contexto de build.

---

## 2026-05-13 — feat: LLM multi-proveedor (Ollama / OpenAI / Anthropic) y Langfuse (trazas + prompt remoto)

- **Dependencias**: `langchain-openai`, `langchain-anthropic`, `langfuse`.
- **config/settings.py**: `LLM_PROVIDER`, claves y modelos OpenAI/Anthropic; variables Langfuse; validación cruzada (API key según proveedor; si `LANGFUSE_PROMPT_NAME` no vacío, exige `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`); propiedad `langfuse_tracing_ready`.
- **agent/llm.py**: `build_llm` devuelve `BaseChatModel` según proveedor.
- **agent/prompts.py**: carga con precedencia inline → Langfuse (`get_prompt` tipo texto, timeout corto) → archivo local; mensajes de error explícitos si no hay fuente válida.
- **commons/langfuse_tracing.py**: registro perezoso del cliente Langfuse por `public_key`.
- **commons/runner.py**: callback Langfuse en `build_graph_invoke_config` si hay credenciales; logs de fallo LLM generalizados por proveedor; streaming tolera `content` no string en chunks.
- **Documentación**: README, `docs/ARCHITECTURE.md`, `docs/skills-implementation.md`, `.env.example`, este changelog; tests de validación en `test/test_settings_multiinstance.py`.

---

## 2026-05-07 — refactor: legibilidad, tipos compartidos y HTTP modular

- **type_defs**: `dicts/domain_literals.py` (`RunStatus`, `TurnStatus`, mensajes/roles); `dicts/event_types.py` (`EVENT_*`, `AgentEventType`); reexports revisados en `type_defs/__init__.py` y `dicts/__init__.py`.
- **commons**: `a2a_constants.py` (códigos JSON-RPC, mensajes, URLs); `commons/__init__.py` solo exporta `TextUtils` para evitar ciclos de importación.
- **agent**: `agent/__init__.py` solo `build_agent` (CLI sigue en `agent.cli:main`); tools de memoria partidas en `memory_serializer.py`, `memory_queries.py`, `memory_tools.py`.
- **database**: `constants.py` para longitudes de columnas; defaults alineados con literales centralizados.
- **services**: estadísticas de runs en `agent_runs_stats_service.py`; docstrings en español en runs/events donde aplica.
- **HTTP**: `agent_turn_guard.py` (exclusión mutua turno HTTP/A2A); rutas REST en `http_api/routers/rest_routes.py`; `app.py` con CORS desde `Settings` (`CORS_ORIGINS`, `CORS_ALLOW_CREDENTIALS`); `state.py` con `status` tipado como `StatusAgent`.
- **Tests**: `test_a2a_inbound.py` fuerza `AGENT_SLUG` + `A2A_ASSISTANT_ID` vacío para que coincidan las URLs con `Settings` tras `load_dotenv`.
- **Docs**: README / `.env.example` con variables CORS; arquitectura actualizada en este mismo cambio.

---

## 2026-04-27 — test: flujo LLM fake (tool calling) y documentación de pytest

- **Tests**: `test/test_fake_llm_tool_flow.py` — conversación simulada con `GenericFakeChatModel` (pregunta de estado de servidor → tool → resumen), sin Ollama ni API remota; caso adicional con `AgentRunCallbackHandler` + mock de `AgentEventsService` (misma secuencia `llm_*` / `tool_*` que CLI/HTTP vía callbacks en `config`).
- **Documentación**: README (sección pytest), `test/README.md` (inventario, comando unificado, **pytest y logs en consola** con `--capture=no` / `--log-cli-level=DEBUG`), `docs/ARCHITECTURE.md` (carpeta `test/`).

---

## 2026-04-19 — feat: multi-instancia (slug, prompt por env, Compose + Postgres)

- **Settings**: `AGENT_SLUG`, `AGENT_DISPLAY_NAME`, `AGENT_CARD_DESCRIPTION`, `SYSTEM_PROMPT`, `SYSTEM_PROMPT_PATH`; `effective_a2a_assistant_id` (A2A local = slug si `A2A_ASSISTANT_ID` vacío); `A2A_REMOTE_ASSISTANT_ID` vacío alinea el default remoto con ese id efectivo.
- **Prompt**: `load_system_prompt_for_settings`; copia versionada `system.promt.default.md`; Dockerfiles copian ambos `.md` de prompt.
- **Logs**: archivo `logs/agent_<slug>.log`. **Agent Card**: `name` desde display name; `description` desde `AGENT_CARD_DESCRIPTION` o fallback genérico con slug.
- **Compose**: `compose.yml` con Postgres (`POSTGRES_DB` = slug) y servicio `agent` (`host.docker.internal` para Ollama en el host).
- **Tests**: `test/test_settings_multiinstance.py`.

---

## 2026-04-19 — feat: A2A embebido, peers por env y tests pytest (sin CI)

- **Servidor A2A (inbound)** en FastAPI: `GET /.well-known/agent-card.json`, `POST /a2a/{assistant_id}` con JSON-RPC `message/send`; mismo grafo y `AgentRunner` que `/chat`. Variables `A2A_ASSISTANT_ID`, `A2A_PROTOCOL_VERSION`.
- **Cliente A2A (outbound)** en el grafo: `A2A_PEER_URLS` (comas, opcional `url|assistant_id`), `A2A_REMOTE_ASSISTANT_ID`; módulo `agent/a2a_peers.py`; tools `a2a_list_remote_agents` y `a2a_send_to_remote`. CLI lista peers al inicio si hay URLs; **no** expone servidor A2A (solo `agent-forge-http`).
- **Dependencias**: `httpx` en runtime; `pytest` y `pytest-asyncio` en grupo **dev**; `[tool.pytest.ini_options]` con `asyncio_mode=auto` y `pythonpath=src`.
- **Tests**: `test/test_a2a_inbound.py`, `test/test_a2a_peers.py`, `test/test_a2a_client_http.py` (cliente outbound con `httpx.MockTransport`; sin workflows de CI en este entregable).
- **Documentación operativa**: README, ARCHITECTURE, A2A_TRES, A2A_LANGCHAIN (estado outbound), Postman, `.env.example`.

---

## Hitos críticos anteriores (resumen)

- **2026-04-19 — Deep Agents**: migración a `deepagents` / `create_deep_agent`, skills en `skills/<nombre>/SKILL.md`, `FilesystemBackend`, tag git `base-agent` como baseline previa.
- **2026-04-16 — Streaming HTTP**: `POST /chat/stream` (SSE) y `stream_agent_turn` unificado en `AgentRunner`.
- **2026-04-16 — Skills runtime** (antes de Deep Agents): carpeta `skills/`, tool `skill_get_guide` y catálogo por turno (luego sustituido por el modelo Deep Agents).
- **2026-04-16 — Memoria en docs**: guías `MEMORIA.md` / skills (luego consolidadas en skills-implementation).
- **2026-04-16 — Checkpointer + store LangGraph**: `AsyncPostgresSaver`, `AgentPostgresStore` / `agent_memory_facts`, migración Alembic asociada; `thread_id` = `chat_id`.
- **2026-04-15 — Renombre AgentForge**: `agent-forge`, script HTTP `agent-forge-http`, loggers y BD por defecto `agent_forge`; CLI `uv run agente`.
- **2026-04-15 — Modelo chats / trazas**: tablas `chats`, `chat_messages`, `agent_runs.chat_id`, tokens en `llm_end` vía callbacks, refactor `ReplyExtractor` / `InterceptorHelpers` / `type_defs` (sin paquete `schemas`), renombre `types` → `type_defs` (colisión con stdlib), tipado `JsonDict`, excepciones de dominio.
- **2026-04-15 y anteriores**: limpieza código muerto, Alembic inicial, fixes import circular `http_api`/`commons`, observabilidad Ollama, etc. Ver `git log` para el detalle completo.
