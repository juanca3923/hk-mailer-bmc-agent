# Scripts de diagnóstico (`test/`)

Herramientas de desarrollo para inspeccionar la base de datos, las memory tools y qué contexto recibe el LLM en cada turno.

**Tests pytest:** opcionales; requieren `uv sync --group dev`. Incluyen A2A con mocks y un flujo de chat/tool con **LLM fake** (sin red ni consumo de tokens).

```bash
uv run pytest test/test_a2a_inbound.py test/test_a2a_inbound_processor.py test/test_a2a_peers.py test/test_a2a_client_http.py test/test_settings_multiinstance.py test/test_skill_catalog.py test/test_fake_llm_tool_flow.py
```

- **A2A y settings:** `test_a2a_*.py`, `test_settings_multiinstance.py`.
- **Skills:** `test_skill_catalog.py` — descubrimiento de `skills/*.md` y `skills/<dir>/SKILL.md`, bloque XML `<skills>` (vacío si no hay guías), extracción de descripción (frontmatter o primer `#`) y lectura dual en `read_skill_guide_json`; usa `tmp_path`, sin BD ni red.
- **LangChain:** `test_fake_llm_tool_flow.py` — pregunta de usuario → razonamiento simulado → `tool_calls` → `ToolMessage` → resumen final, usando `GenericFakeChatModel`; un test pasa por `AgentRunCallbackHandler` con `config["callbacks"]` como el runner (mock de `insert_event`, sin Postgres).

**Logs en consola durante pytest:** por defecto pytest **captura** stdout/stderr; los mensajes del `logging` del proyecto (p. ej. interceptors) siguen yéndose al fichero `logs/agent_<AGENT_SLUG>.log`, pero **no los verás en la terminal** si el test pasa. Para ver en consola la misma actividad (y trazas de logging con `--log-cli-level`):

```bash
uv run pytest test/test_fake_llm_tool_flow.py --capture=no --log-cli-level=DEBUG
```

- `--capture=no` (o `-s`): no captura la salida; los `StreamHandler` hacia stderr vuelven a mostrarse como fuera de pytest.
- `--log-cli-level=DEBUG` (o `INFO`, etc.): activa el visor de logs de pytest; combina con `LOG_LEVEL` en `.env` si quieres alinear niveles (p. ej. `LOG_LEVEL=DEBUG` para `logger.debug` de la app).

Los scripts siguientes **no** son pytest: son ejecutables a demanda para depuración manual.

---

## Estructura

```
test/
  test_runs.py         ← runs: tarea activa, listado y eventos de una run
  test_chats.py        ← chats: búsqueda, mensajes e historial en BD (contexto tipo checkpointer)
  test_a2a_inbound.py       ← pytest: endpoint A2A (mocks)
  test_a2a_inbound_processor.py ← pytest: processor inbound en commons
  test_a2a_peers.py     ← pytest: parseo de respuestas A2A
  test_a2a_client_http.py ← pytest: cliente outbound (MockTransport)
  test_settings_multiinstance.py ← pytest: AGENT_SLUG, prompt path, A2A efectivo
  test_skill_catalog.py    ← pytest: catálogo XML de skills y lectura de guías (tmp_path)
  test_fake_llm_tool_flow.py ← pytest: flujo tool-calling con GenericFakeChatModel (sin Ollama)
  output/              ← archivos .log generados (ignorados por git)
    .gitkeep
```

---

## Requisitos previos

- El proyecto instalado con `uv sync`.
- `.env` configurado con `DATABASE_URL` apuntando a la base de datos.
- La base de datos accesible (Postgres corriendo con el esquema aplicado) para `test_runs.py` y `test_chats.py`.

Ejecutar siempre desde la **raíz del proyecto**.

---

## `test_runs.py` — diagnóstico de runs

Inspecciona las ejecuciones del agente llamando directamente a las memory tools correspondientes.

### Secciones del log generado

```
[1] TAREA ACTIVA        → memory_get_current_task()
[2] ÚLTIMAS RUNS        → memory_list_recent_runs(limit=N)
[3] EVENTOS DE RUN      → memory_get_run_events(run_id=<id>)
```

La sección `[3]` usa automáticamente el run más reciente de `[2]`, salvo que se indique `--run-id`.

### Comandos

```bash
# Ejecución básica — toma el run más reciente automáticamente
uv run python test/test_runs.py

# Inspeccionar un run específico
uv run python test/test_runs.py --run-id <uuid>

# Cambiar cuántas runs se listan en [2]
uv run python test/test_runs.py --limit 10

# Combinar opciones
uv run python test/test_runs.py --run-id <uuid> --limit 10
```

### Argumentos

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--run-id` | auto (primer run de [2]) | UUID del run a inspeccionar en [3] |
| `--limit` | `5` | Cuántas runs listar en [2] |

---

## `test_chats.py` — diagnóstico de chats y contexto LLM

Inspecciona el historial de chats y el contexto que se obtiene desde la BD (el hilo activo lo rehidrata el **checkpointer** de LangGraph con `thread_id=chat_id`).

### Secciones del log generado

```
[1] BÚSQUEDA DE CHATS   → memory_search_chats(query="...")
[2] MENSAJES DEL CHAT   → memory_get_chat_messages(chat_id=<id>, limit=N)
[3] CONTEXTO EN BD      → mensajes convertidos a LangChain (referencia para depuración)
```

La sección `[3]` ayuda a comparar el historial persistido en BD con lo que el checkpointer puede rehidratar en el grafo.

### Comandos

```bash
# Buscar chats que contengan una palabra (case-insensitive)
uv run python test/test_chats.py --query "nginx"

# Ver todos los chats (query vacío muestra el más reciente)
uv run python test/test_chats.py

# Ir directo a un chat específico sin buscar
uv run python test/test_chats.py --chat-id <uuid>

# Cambiar cuántos mensajes cargar en [2]
uv run python test/test_chats.py --chat-id <uuid> --limit 30
```

### Argumentos

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--query` | `""` | Texto a buscar en el historial (ILIKE) |
| `--chat-id` | auto (primer resultado de [1]) | UUID del chat; salta la búsqueda |
| `--limit` | `20` | Mensajes a cargar en [2] |

---

## Salida

Cada ejecución escribe un archivo en `test/output/`:

```
test/output/runs_20260416_103045.log
test/output/chats_20260416_104512.log
```

Los `.log` están en `.gitignore` y no se versionan. La carpeta `output/` sí se commitea (via `.gitkeep`).

En consola solo aparece una línea indicando la ruta del archivo generado:

```
Log escrito en test/output/chats_20260416_104512.log
```
