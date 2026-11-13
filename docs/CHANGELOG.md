# Changelog

Registro de cambios **relevantes** del proyecto **agent-bmc**. Condensado a lo que no es
obvio desde el código; el detalle línea por línea sigue en `git log -- docs/CHANGELOG.md`.

---

## 2026-11-13 — feat: topes por run para el modelo y las tools

- Ningún tope limitaba al agente (el default de LangGraph son ~10.000 pasos): ante un fallo persistente el modelo repitió `bmc_create_work_order` 28 veces seguidas (~21k tokens de entrada por vuelta) y siguió corriendo aunque el llamador (el mailer) ya había abandonado por tiempo.
- Nuevo `agent/middleware/run_limits.py` (`ToolCallLimitMiddleware` y `ModelCallLimitMiddleware` de LangChain), configurable: `AGENT_MAX_MODEL_CALLS_PER_RUN` (20; al superarlo el run termina con error, que el llamador A2A ve como fallo), `AGENT_MAX_TOOL_CALLS_PER_RUN` (15; las sobrantes se bloquean y el modelo responde) y `BMC_MAX_CREATE_CALLS_PER_RUN` (3 para cada `bmc_create_*`). `0` desactiva cada tope.

---

## 2026-11-13 — fix: tickets abiertos en modo automático y Agent Card con los datos requeridos

- En modo automático (A2A) el agente ya no cierra el ticket: solo lo crea (y agrega la nota) y lo deja abierto; `Estado final: Abierto`. El cierre sigue disponible en modo interactivo.
- La descripción por defecto de la Agent Card (antes "Agente operativo Linux…") dice qué necesita el agente: el correo real del solicitante y la descripción del caso para crear, y el número del ticket o el correo para consultar; y que los casos quedan abiertos. `AGENT_CARD_DESCRIPTION` sigue pudiendo sobrescribirla.

---

## 2026-11-13 — fix: `tool_end` y `tool_error` registran el nombre y la duración de la tool

- Los logs mostraban `tool=None duration=0.000s`: el callback buscaba el nombre por `tool_call_id`, que LangChain solo entrega al iniciar la tool. Ahora se usa el `run_id`, igual en los tres callbacks.

---

## 2026-11-13 — feat: catálogo único de categorización `categorias-mail-drive`

- Las skills `categorias-eventos` y `categorias-usuario` se reemplazan por `categorias-mail-drive`, con la tabla de Requerimientos (con palabras clave para elegir la fila) y la de Incidentes de la mesa de servicio. Sin cambios de código.
- Los niveles de producto 2 y 3 que la tabla original dejaba vacíos se completaron con combinaciones existentes del catálogo anterior (aproximadas); `Prioridad` y `Escalamiento 1` quedan vacíos y se usan los defaults de la tool. **Pendiente**: confirmar ambos con la mesa de servicio.
- **Acción operativa**: si el prompt vive en Langfuse, reemplazar allí las referencias a `categorias-eventos`/`categorias-usuario`.
## 2026-11-13 — fix: "la persona no existe" es un fallo definitivo

- El mensaje de persona no encontrada en `CTM:People` ahora termina con "Es definitivo: no reintentes ni busques otra forma de crearlo; informa este error." (el JSON `success:false` no cambia). Antes el modelo repetía `bmc_create_work_order` decenas de veces cambiando tildes y consultando `memory_*`.
- `system.promt.md`: un `success:false` de una tool de escritura es definitivo para esa solicitud; en modo automático se responde de inmediato con `Estado final: Error — <mensaje>`.

---

## 2026-11-13 — refactor: tools del LLM en clases y errores siempre visibles

- Cada archivo de `agent/internal_tools/` expone una clase (`BmcTools`, `WorkOrderTools`, `IncidentTools`, `StagedFilesTools`, `DatetimeTools`, `MemoryTools`, `SkillTools`, `A2APeerTools`) con un `get_tools()` estático; `_ALL_BMC_TOOLS` y las funciones `get_*_tools` desaparecen.
- Nueva base `ToolSet` (`internal_tools/base.py`): exige `description` explícita y convierte cualquier excepción inesperada en un mensaje legible para el LLM (tool, tipo y texto recortado; el traceback queda en el log). Los argumentos inválidos se describen por campo, sin el valor recibido.
- Sin cambios en nombres, parámetros ni salida de las tools (contrato verificado idéntico).

---

## 2026-11-13 — refactor: logging para rastreo sin datos sensibles

- Niveles revisados: INFO con hitos (arranque, turno/run/tick con id y duración, llamadas a Graph/BMC/A2A con estado y duración, decisiones sobre correos o tickets) y DEBUG con el detalle (textos recortados a 200 caracteres, tamaños).
- El system prompt ya no sale dos veces a INFO: INFO muestra origen, nombre, label/versión y longitud; el texto completo va una sola vez en DEBUG.
- Se corrigieron fugas: URL de Postgres con contraseña en el checkpointer, entradas de tools y previews del LLM a INFO, cuerpos de BMC, URLs de peers A2A y consultas de búsqueda. `httpx` y `httpcore` quedan en WARNING porque registran la URL completa (con correos en la query de BMC). Las direcciones de terceros se enmascaran (`mask_email`).
- **Acción operativa**: ninguna; con `LOG_LEVEL=DEBUG` se obtiene el detalle de diagnóstico.

---

## 2026-11-13 — refactor: reorganización del repositorio por capas

- `src/bmc/` desaparece y su contenido se reparte por capas: `config/bmc_settings.py`, `constants/bmc/` (campos, mensajes, API, tickets, adjuntos, defaults), `type_defs/models/bmc/`, `type_defs/ports/`, `type_defs/enums/` (`StrEnum` de estados de WO/incidente y `StagedSkipReason`), `commons/bmc/` (lógica pura), `services/bmc/`, `services/startup/preflight.py`, `agent/runtime/`, `agent/observability/` y `http_api/`.
- Reglas nuevas (capas sin imports hacia arriba, un archivo una responsabilidad, nada suelto en `commons/` ni `services/`) en `docs/ARCHITECTURE.md`, `CLAUDE.md` y las reglas de `.claude/` y `.cursor/`.
- Sin cambios de comportamiento ni de contrato HTTP. Los paquetes de `pyproject.toml` y `mypy.ini` cambian (`src/bmc` → `src/constants`).
- **Acción operativa**: ninguna; las rutas de importación internas cambiaron.

---

## 2026-11-12 — fix: `Dockerfile.dev` no pierde `/bin/sh` al crear `appuser`

- **`Dockerfile.dev`**: `useradd` pasa al inicio de la imagen, y `uv sync` y `pip uninstall` quedan en capas distintas (`--link-mode copy`). En una sola capa, el image store containerd de Docker la guardaba vacía y el `RUN useradd` siguiente fallaba con `stat /bin/sh: no such file or directory`. También crea `/app/data/ticket_files` y `/app/logs` con dueño `appuser`.
- **Acción operativa**: reconstruir la imagen de desarrollo (`docker compose build` apuntando a `Dockerfile.dev`).

---

## 2026-11-12 — feat: autochequeo de arranque del campo de estado de `CTM:People`

- Al arrancar, una consulta de prueba a `CTM:People` (dirección ficticia `.invalid`; no busca a nadie) pide el campo `AR_FIELD_PEOPLE_STATUS`. Si BMC lo rechaza (HTTP 400) el log trae un warning `preflight:` que remite a confirmar el nombre del campo; otros fallos se registran sin culpar al campo. Tiempo límite de 60 s y **nunca bloquea el arranque** (`bmc/libs/preflight.py`).

---

## 2026-11-12 — feat: endpoint para verificar que un correo es un origen válido

- **`POST /people/verify`** (`{"email"}` → `{"exists", "enabled"}`): consulta `CTM:People` por `Internet E-mail` y comprueba el estado de la persona (`AR_FIELD_PEOPLE_STATUS`, `Profile Status`; **nombre del campo pendiente de confirmar contra la instancia BMC**). Mismo desempate que la creación de tickets (el bot `AgentesIA` que comparte correo no decide). Sin LLM ni tokens. `search_person_by_email` ahora pide también el estado.
- **Seguridad**: exige `X-API-Key` = `BMC_VERIFY_API_KEY` (comparación en tiempo constante); sin clave configurada responde 503; devuelve solo `exists`/`enabled`; el error de BMC sale como 502 sin detalle.
- **Acción operativa**: definir `BMC_VERIFY_API_KEY` (Secret de Kubernetes, el mismo valor en el mailer) y confirmar el nombre del campo de estado.

---

## 2026-11-12 — refactor: esqueleto compartido de las escrituras con guardas

- `run_guarded_write` (`bmc/libs/helpers/guarded_write.py`) reemplaza el bloque repetido (escritura habilitada, ticket resuelto, no `Closed`, `try/except MCPClientError`) de `add_note`, `add_attachment`, `update_status` y `close` en `IncidentOperations` y `WorkOrderOperations`; `WorkLogInput` unifica los campos del work log y `ticket_tool_helpers.py` las piezas comunes de las tools. Sin cambio de comportamiento ni de esquemas de las tools; pylint vuelve a 10,00 (sin los 6 avisos `R0801`).
- `Dockerfile`/`Dockerfile.dev`: `uv sync --link-mode copy` para evitar la capa vacía de containerd.

---

## 2026-11-12 — feat: adjuntar archivos staged desde carpeta compartida y confinar rutas de adjuntos

- **Seguridad (cambio de comportamiento)**: `BaseToolHandler.load_attachment` solo lee archivos dentro de `BMC_ATTACHMENT_BASE_DIR`; la ruta se resuelve por completo (`..` y enlaces simbólicos incluidos) y lo que quede fuera se rechaza. **Sin definir esa variable, los adjuntos quedan deshabilitados**, también `bmc_add_incident_attachment` / `bmc_add_work_order_attachment`, que antes aceptaban cualquier ruta legible del contenedor.
- **`bmc_attach_staged_files`** (tool nueva, 15 en total): recibe `ticket_type`, `ticket_number` y `staging_id`; sube cada archivo de `<BMC_ATTACHMENT_BASE_DIR>/<staging_id>/manifest.json` como una entrada del log de actividad. Los archivos que superan `BMC_MAX_ATTACHMENT_BYTES` o que falten no se suben y se listan en una nota del ticket. Nunca recibe rutas ni bytes. Lógica en `src/bmc/libs/helpers/staged_files.py`.
- **Acción operativa**: definir `BMC_ATTACHMENT_BASE_DIR` y montar esa carpeta (solo lectura) compartida con el agente que deja los archivos; en Kubernetes, un volumen `ReadWriteMany`. Sin cambios en la API HTTP.

---

## 2026-11-12 — chore: mypy como verificador de tipado estático

- **Dependencia dev**: `mypy==2.4.1` en el grupo `dev` de `pyproject.toml` (y `uv.lock`). Se ejecuta con `uv run mypy`.
- **`mypy.ini`** (nuevo, igual que en `hk-mailer-agent`): `mypy_path = src`, los 9 paquetes de `src/` (incluye `bmc`), plugin `pydantic.mypy`, `check_untyped_defs`, `disallow_untyped_defs`, `disallow_any_generics`, `warn_return_any`, `warn_unused_ignores`, `ignore_missing_imports`; `alembic.*` con `ignore_errors`. `warn_unreachable` queda desactivado a propósito.
- **Baseline en 0 errores** (74 iniciales): solo anotaciones y ajustes de tipos, sin cambios de lógica. Los archivos comunes con el mailer reciben las mismas correcciones (callback de eventos, `runner`, `store`, `cli`, `lifespan` de FastAPI, `StatsResponse.model_validate`). Específicos del BMC: `EntryValuesMapper.wrap_entry_body` devuelve `dict[str, JsonValue]` (los `dict` son invariantes en el valor y rechazaban el cuerpo en `BmcClient`), `cast` donde `httpx` y `ToonEncoder` devuelven `Any`, dos `# type: ignore` sobrantes eliminados y `HuggingFaceEndpoint` recibe `model=` en lugar de `repo_id=` (son excluyentes; `test_llm_huggingface.py` se ajusta).
- **`# type: ignore[valid-type]`** en 3 parámetros `Literal[<constante>]` de las tools (`WORK_ORDER_STATUSES`, `INCIDENT_STATUSES`): en runtime la tupla se expande a `Literal` con cada valor (y alimenta el `enum` del esquema que ve el LLM), pero mypy no admite una variable ahí.
- **Acción operativa**: ejecutar `uv sync --group dev` y, antes de merge, `uv run mypy` junto a `ruff` y `pylint`. Aún no corre en el pipeline de Azure/SonarQube.
- **Pendiente previo, no tocado**: 4 tests de `test_incident_operations_create.py` fallan desde antes (`CreateIncidentInput` exige `reporter_email` y los tests no lo envían).

---

## 2026-11-12 — chore: Python 3.14 y actualización de dependencias

- **Python**: el proyecto pasa a Python **3.14**, el mismo que `hk-mailer-agent`. `requires-python = ">=3.14"`, imágenes `python:3.14-slim` en `Dockerfile` y `Dockerfile.dev`, y `target-version`/`py-version` alineados en `ruff.toml` y `.pylintrc`. Antes: `>=3.11`, Docker en 3.12, ruff/pylint en 3.13.
- **Dependencias**: 25 de las 28 dependencias directas suben (quedan igual `langchain-ollama`, `httpx` y `toon-formatter`, ya en su última versión) y el `uv.lock` completo se resuelve con la última versión con **al menos 7 días de publicada** (corte 2026-11-05; ningún artefacto del lock es posterior). `pip-audit` sobre el lock: sin vulnerabilidades conocidas.
- **`Dockerfile`**: el `RUN` que instalaba `uv`, sincronizaba el venv y desinstalaba `uv` se divide en dos (`uv sync` / `pip uninstall`). En una misma capa, el image store containerd de Docker puede generar una imagen vacía que falla al arrancar con `unable to find user appuser`. El resultado funcional es el mismo.
- **`sqlalchemy[asyncio]`**: SQLAlchemy 2.1 ya no instala `greenlet` por defecto; el extra `asyncio` lo trae y evita un `ImportError` al importar los módulos de base de datos.
- **`src/commons/langfuse_tracing.py`**: `opentelemetry-exporter-otlp-proto-http` 1.45 cambió su transporte HTTP, y el parche de `_certificate_file` de `LANGFUSE_SSL_VERIFY=false` dejó de funcionar. Ahora se inyecta `RequestsHTTPTransport(verify=False)` vía `_transport`. Verificado contra un servidor HTTPS autofirmado: el exportador normal lo rechaza y el nuestro entrega el span.
- **Acción operativa**: reconstruir las imágenes Docker y ejecutar `uv sync --group dev`. Sin cambios en variables de entorno ni en la API.

---

## 2026-09-16 — refactor: separa descripción de tool (LLM) del docstring (humanos)

- `@tool` sin argumento enviaba al LLM el docstring NumPy completo (RST, `Returns`
  repetido en las 21 tools, y en 2 casos un placeholder de `Parameters` que violaba el
  propio estándar). Ahora cada tool pasa `@tool(description=...)` /
  `StructuredTool.from_function(description=...)` explícito y corto; el docstring queda
  solo para humanos. Convención en `estandar-python.md`/`.mdc`.
- `bmc_tools.py` superó las 1000 líneas al agregar las descripciones → dividido en
  `bmc_tools.py` (agregador) + `bmc_work_order_tools.py` + `bmc_incident_tools.py`. El
  import cíclico resultante se resolvió moviendo el singleton `BaseToolHandler` a
  `bmc/libs/tool_handler.py` (`get_shared_handler`, sin depender de `agent.internal_tools`).
- Auditoría de seguimiento: un `Field(description=...)` no debe mezclar "qué es el dato"
  con "cómo conseguirlo" (ej. "pregúntale al usuario, o tómalo de A2A" — eso es protocolo,
  ya vive en `system.promt.md`) ni nombrar mecanismos internos no accionables por el LLM
  (ej. `CTM:People`). Nuevo skill global `tool-ia-mcp` documenta el estándar (aplica igual
  a tools MCP: `Tool.description` + `inputSchema.properties.*.description`).

## 2026-09-16 — fix: recorta info de tickets a título/estado/grupo asignado (privacidad)

- `bmc_get_work_order`/`bmc_get_incident` devolvían el dict crudo completo de BMC (~150
  campos, incluida descripción detallada y notas). Las 4 tools de consulta (incluidas las
  `*_by_email` nuevas) ahora devuelven solo título/estado/grupo asignado.
- Hallazgo verificado contra BMC real: en Work Order, el alias de creación
  `"Support Group Name"` no refleja el grupo real al leerlo de vuelta (siempre muestra el
  desk fijo) — el campo correcto es `"ASGRP"`. En incidentes, `"Assigned Group"` sí es
  confiable.

## 2026-09-16 — feat: tools para listar tickets por correo del solicitante

- Nuevas `bmc_list_work_orders_by_email`/`bmc_list_incidents_by_email` (14 tools BMC en
  total). Verificado contra BMC real antes de implementar: WO filtra por
  `'Customer Internet E-mail'`, incidente por `'Internet E-mail'` — ambos son el correo
  crudo pasado a `reporter_email` al crear, no el login resuelto en `CTM:People`. Resultados
  capados en `MAX_TICKETS_BY_EMAIL_RESULTS` (30), con `total_found`/`truncated` en la
  respuesta.
- Bug preexistente corregido de paso: `bmc_get_work_order` leía el asunto desde
  `"Summary"` (vacío en este formulario); el campo real es `"Description"`.

## 2026-09-16 — deuda técnica: confirmación real (graph-level) antes de cerrar un ticket

- Confirmado en pruebas: el guardarraíl de prompt (pedir confirmación antes de cerrar un
  ticket cuyo ID vino de una búsqueda en memoria) no es garantizable solo con texto — el
  modelo encadena tool calls libremente dentro de un turno, sin pausar.
- Solución evaluada y viable, pendiente de implementar: `HumanInTheLoopMiddleware` de
  LangChain (usa `interrupt()` de LangGraph, persistido en el checkpointer ya en uso).
  Costo real: `runner.py` asume hoy que un turno siempre termina en respuesta final;
  requeriría un estado `awaiting_confirmation`, reinterpretar el siguiente mensaje del
  usuario como aprobación/rechazo, y decidir la política para A2A (`system.promt.md` dice
  hoy que A2A nunca pide confirmación — el middleware pausaría también esas llamadas salvo
  que se desactive ahí explícitamente).
- Mitigación actual: solo guardarraíles de prompt (reducen la frecuencia, no la eliminan).

## 2026-09-16 — feat: turnos concurrentes en HTTP/A2A, configurable por env

- Nueva `HTTP_ALLOW_CONCURRENT_TURNS` (default `True`). Antes, un segundo turno mientras
  había uno en curso siempre devolvía `409`; ahora es opcional porque cada turno ya está
  aislado por `chat_id`/`thread_id` en el checkpointer de Postgres.
- `AgentState` pasa de flag booleano a contador de turnos (`try_begin_task`/`end_task`),
  atómico sin `asyncio.Lock` (no hay `await` entre chequeo e incremento). Eliminado código
  muerto: `app.state.agent_lock`, `ChatHandler.check_not_busy_or_raise`.

---

## 2026-09-14

- **Catálogos genéricos ficticios → catch-all real de WO**: eliminados
  `categorias-incidentes.md`/`categorias-requerimientos.md` (muestras del ambiente de
  pruebas, no el catálogo real). Un caso fuera de todo dominio conocido ahora se crea
  siempre como Work Order con una categorización catch-all fija, documentada en
  `guia-creacion-tickets` — vive en el skill (no en código/env) porque `skill_get_guide`
  se lee en vivo en cada llamada, mientras que env vars solo se cargan una vez al iniciar.
- **`description` de incidente rechazado por BMC sobre 100 caracteres**: confirmado contra
  BMC real (`Maximum length -100`, rechaza toda la petición, no trunca). Nueva
  `INCIDENT_DESCRIPTION_MAX_LENGTH=100`; el límite se expresa como
  `Annotated[str, Field(max_length=...)]` — necesario para que llegue al schema que ve el
  LLM.
- **Identidad real del solicitante vía `CTM:People` (`reporter_email`)**: antes todo
  ticket se creaba con una identidad fija ("Agentes IA"). Ahora `reporter_email` es
  obligatorio; se resuelve `First/Last Name` real contra `CTM:People` y, si no se
  encuentra esa persona, no se crea ningún ticket. `Internet E-mail` no es único en BMC —
  la desambiguación prefiere un `Remedy Login ID` con forma de correo sobre uno tipo bot.
- **Nueva tool `get_current_date`**: el agente no tenía forma de saber la fecha/hora real.
  Lee el reloj del contenedor, lo convierte a `AGENT_TIMEZONE` (default `America/Bogota`),
  con nombres de día/mes en español por tablas fijas (sin depender del locale del SO).
- **Refuerza calidad de asunto/descripción de tickets**: `summary`/`description`/
  `detailed_description` solo tenían `min_length=1`, sin guía de contenido. Se agregaron
  criterios (+ ejemplo bueno/malo) en `guia-creacion-tickets` y en los
  `Field(description=...)` correspondientes.

## 2026-09-02 a 2026-09-07 — catálogos de categorización por dominio

- **`categorias-eventos.md`** (creado 2026-09-02, completado 2026-09-07 con Categoría
  Operacional 1/2/3): catálogo real de la mesa de servicio para "eventos" — disponibilidad
  (ausencia/caída/degradación) = Incidente; capacidad (aumento/adición planeada) = Work
  Order.
- **`categorias-usuario.md`** (2026-09-01): catálogo real de "usuario de red"; su columna
  `Tipo Servicio` decide Incidente vs. Work Order con **prioridad** sobre el heurístico
  semántico genérico de `guia-creacion-tickets` (que pasa a ser el fallback). Motivado por
  un caso real donde el LLM ignoró un catálogo de dominio ya cargado en el prompt y decidió
  por heurístico — la causa fue de orden/precedencia, no de código.
- **`guia-creacion-tickets` consolida el procedimiento** (2026-09-01): mapeo
  columna→parámetro, traducción de prioridad ES→EN y regla de fallback quedan en un solo
  lugar; las skills de dominio se recortan a solo su tabla de datos (~22% menos bytes en
  conjunto).

## 2026-09-01 — soporte Hugging Face como proveedor LLM

- `LLM_PROVIDER=huggingface` vía HF Inference Providers (`ChatHuggingFace` +
  `HuggingFaceEndpoint`), con `HUGGINGFACE_PROVIDER`/`HUGGINGFACE_BILL_TO` opcionales y
  `HUGGINGFACE_ALLOW_LEGACY_TLS` (solo dev, para redes corporativas con inspección TLS de
  clave débil). Riesgo conocido: el tool calling vía HF no está garantizado por
  modelo/proveedor, y este agente depende de tool calling para todo — validar el modelo
  elegido antes de producción.
- `llm_temperature`/`huggingface_max_new_tokens` pasan a ser configurables por env (antes
  hardcoded); cobertura de test agregada tras una auditoría cruzada desde otra sesión.

## 2026-07-29 y 2026-07-30 — sincronización con `bmc-mcp`

- Las 12 tools se renombran con prefijo `bmc_*` (paridad con el servidor MCP). Se portan
  guards de negocio (`require_not_closed`, `require_submitter`), se corrige el formulario
  de notas de incidente (escribía contra `WOI:WorkInfo` en vez de `HPD:WorkLog`), y se
  reescribe el cierre como 2-3 PUT con toma de propiedad previa (sin exigir `In Progress`).
- `bmc_create_work_order` gana `assigned_group` (antes se creaba sin grupo de soporte).
  `status` pasa de `str` a `Literal[...]` real — un intento previo con
  `Field(json_schema_extra={'enum': ...})` no llegaba al schema del LLM porque LangChain
  reconstruye el `FieldInfo` del `args_schema` sin copiar `json_schema_extra`; `Literal` sí
  sobrevive esa reconstrucción por quedar en la anotación, no en los metadatos.

## 2026-09-10/11 y 2026-06-26 — hallazgos de campos de BMC

- **Confirmado en Postman**: BMC ignora `Assigned Group` (incidente) o
  `Support Group Name` (Work Order) si no viajan junto con dos campos fijos adicionales —
  `Assigned Support Company/Organization` (incidente) o `Support Company/Organization`
  (WO); nombres de campo distintos entre formularios. Sin el fix, el ticket se creaba en
  la cola de asignación por defecto de BMC, sin error visible.
- **2026-06-26**: valores de negocio (compañía, identidad fija) movidos a
  `business_defaults.py`, fuera del schema de la tool — el LLM rellenaba estos campos con
  texto libre del usuario (ej. "Arus S.A.S." en vez de "ARUS"), causando error 400 en BMC.

## 2026-06-25 — creación del proyecto `agent-bmc`

- Proyecto nuevo basado en `agent_forge`; la capa BMC (`config`, `libs`, `type_defs`) se
  portó de `bmc-mcp` con 12 tools LangChain envolviendo BMC Helix AR REST directamente
  (sin servidor MCP).

---

## Historial previo (`agent_forge`) — resumen

A partir de 2026-04-19 se omiten cambios meramente documentales; detalle fino en `git log`.

- **2026-05-21**: manejo centralizado de errores de tool (`ToolAgentError`,
  `configure_tool_error_handling`), prompt caching OpenAI/Anthropic, servicios de runs
  dedicados (`agent_runs_service.py`).
- **2026-05-19**: catálogo de skills inyectado en el system prompt (bloque `<skills>`,
  descubrimiento por convención de archivo, sin inyección por turno); rama `agent-base`
  con `create_agent` de LangChain estándar (sin `deepagents`) en paralelo a
  `deep-agent-base`.
- **2026-05-13/14**: LLM multi-proveedor (Ollama/OpenAI/Anthropic) + Langfuse (trazas y
  prompt remoto); A2A outbound exige `url|agent_id`; versiones exactas y Docker/CI
  alineados con `uv.lock`.
- **2026-05-07**: refactor de legibilidad — tipos compartidos (`type_defs/dicts`),
  módulos HTTP separados (`agent_turn_guard.py`, `routers/rest_routes.py`), CORS
  configurable por `Settings`.
- **2026-04-27 / 2026-04-19**: tests con LLM fake (`GenericFakeChatModel`, sin Ollama ni
  API remota); soporte multi-instancia (slug, prompt por env, Compose + Postgres); A2A
  embebido (inbound + outbound) con tests pytest.

## Hitos críticos anteriores (resumen)

- **2026-04-19 — Deep Agents**: migración a `deepagents`/`create_deep_agent`, skills en
  `skills/<nombre>/SKILL.md`, `FilesystemBackend`, tag git `base-agent` como baseline previa.
- **2026-04-16 — Streaming HTTP**: `POST /chat/stream` (SSE) y `stream_agent_turn`
  unificado en `AgentRunner`.
- **2026-04-16 — Skills runtime** (antes de Deep Agents): carpeta `skills/`, tool
  `skill_get_guide` y catálogo por turno (luego sustituido por el modelo Deep Agents).
- **2026-04-16 — Memoria en docs**: guías `MEMORIA.md`/skills (luego consolidadas en
  skills-implementation).
- **2026-04-16 — Checkpointer + store LangGraph**: `AsyncPostgresSaver`,
  `AgentPostgresStore`/`agent_memory_facts`, migración Alembic asociada;
  `thread_id` = `chat_id`.
- **2026-04-15 — Renombre AgentForge**: `agent-forge`, script HTTP `agent-forge-http`,
  loggers y BD por defecto `agent_forge`; CLI `uv run agente`.
- **2026-04-15 — Modelo chats/trazas**: tablas `chats`, `chat_messages`,
  `agent_runs.chat_id`, tokens en `llm_end` vía callbacks, renombre `types` → `type_defs`
  (colisión con stdlib).
- **2026-04-15 y anteriores**: limpieza de código muerto, Alembic inicial, fixes de
  import circular `http_api`/`commons`, observabilidad Ollama. Ver `git log` para el
  detalle completo.
