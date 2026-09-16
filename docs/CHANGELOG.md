# Changelog

Registro de cambios **relevantes** del proyecto **agent-bmc**.

---

## 2026-09-16 — feat: nuevas tools para listar tickets por correo del solicitante

- **Problema**: no existía forma de consultar los tickets de una persona — `bmc_get_work_order`/
  `bmc_get_incident` solo buscan por ID exacto, y no había ningún método que filtrara por
  solicitante.
- **Verificado contra BMC antes de implementar** (no se adivinó el campo): probando con un
  correo real, `WOI:WorkOrderInterface` acepta filtrar por `'Customer Internet E-mail'`
  (guarda el `reporter_email` crudo pasado al crear, no el login resuelto en `CTM:People`) y
  `HPD:IncidentInterface` acepta filtrar por `'Internet E-mail'` (mismo comportamiento: correo
  crudo, no login resuelto).
- **Cambio**: dos tools nuevas, `bmc_list_work_orders_by_email` y
  `bmc_list_incidents_by_email`. Devuelven una fila corta por ticket (id, status,
  resumen/descripción) — no el detalle completo que da `bmc_get_work_order`/`bmc_get_incident`
  para un ticket puntual — capadas en `MAX_TICKETS_BY_EMAIL_RESULTS` (30) vía un parámetro
  `limit` opcional, con `total_found`/`truncated` en la respuesta para que el agente sepa si
  hay más resultados de los mostrados.
- **Archivos**: `src/bmc/libs/constants.py` (`AR_FIELD_WO_CUSTOMER_EMAIL`,
  `AR_FIELD_INCIDENT_REPORTER_EMAIL`, `MAX_TICKETS_BY_EMAIL_RESULTS`),
  `src/bmc/libs/api_client.py` (`search_work_orders_by_email`, `search_incidents_by_email`),
  `src/bmc/type_defs/inputs.py` (`TicketsByEmailInput`), `src/bmc/type_defs/outputs.py`
  (`WorkOrdersByEmailData`/`IncidentsByEmailData` y sus filas), `src/agent/internal_tools/bmc_tools.py`
  (las dos tools nuevas, registradas en `_ALL_BMC_TOOLS`), `test/test_bmc_tools.py`,
  `CLAUDE.md`, `system.promt.md`.
- **Ahora son 14 tools BMC** (antes 12).
- **Bug preexistente encontrado y corregido de paso**: `bmc_get_work_order` (y la nueva
  `bmc_list_work_orders_by_email`) leían el asunto de una Work Order desde la clave
  `"Summary"`, que no existe con contenido en `WOI:WorkOrderInterface` (`z1D_Summary` existe
  en el formulario pero siempre viene vacío) — el campo real es `"Description"` (el mismo al
  que mapea el parámetro `summary` de `bmc_create_work_order`). Confirmado contra BMC real:
  `bmc_get_work_order` siempre había devuelto el resumen vacío en producción. Corregido en
  `_wo_detail_from_search` (`src/agent/internal_tools/bmc_tools.py`); agregado test de
  regresión (`test_bmc_get_work_order_summary_comes_from_description_field`).

---

## 2026-09-16 — deuda técnica: confirmación real (graph-level) antes de cerrar un ticket

- **Problema confirmado en pruebas**: el guardarraíl de prompt que exige "pide confirmación
  antes de cerrar un ticket cuyo ID salió de una búsqueda en memoria" (ver entrada de
  "guardarraíl contra memoria cruzada" más abajo) **no se puede garantizar solo con texto**.
  Reproducido en vivo: el agente llamó `memory_get_chat_messages` → `memory_list_recent_runs`
  → `bmc_close_incident` **en el mismo turno**, sin pausar a preguntar — el modelo puede
  encadenar tool calls libremente dentro de un turno (patrón ReAct) y nada lo obliga a
  detenerse, sin importar qué tan explícita sea la instrucción del prompt.
- **Solución evaluada y confirmada viable, pendiente de implementar**:
  `langchain.agents.middleware.human_in_the_loop.HumanInTheLoopMiddleware` (ya disponible en
  `langchain==1.2.15`, instalado en este proyecto) usa el `interrupt()` nativo de LangGraph
  — un corte real de ejecución del grafo, persistido en el checkpointer (ya usamos
  `AsyncPostgresSaver`, sin infraestructura nueva). Se pasaría como
  `create_agent(..., middleware=[HumanInTheLoopMiddleware(interrupt_on={"bmc_close_work_order": True, "bmc_close_incident": True})])`
  en `src/agent/agent.py`.
- **Por qué queda pendiente (costo de integración real, no trivial)**:
  - `src/commons/runner.py` (`run_agent_turn`/`stream_agent_turn`) asume hoy que `ainvoke`/
    `astream` siempre terminan en una respuesta final; con `interrupt()` el grafo queda
    pausado a mitad de camino y hay que detectarlo, convertir el `HITLRequest` en una
    pregunta legible para el usuario, y **no** marcar el run como terminado.
  - El siguiente mensaje del usuario en ese chat deja de ser texto libre: hay que
    interpretarlo como una decisión (`approve`/`reject`) y resumir el grafo con
    `Command(resume=...)`, no volver a invocarlo normal.
  - `AgentTurnResult`/`ChatResponse` necesitan un estado nuevo (algo como
    `awaiting_confirmation`) para que HTTP y A2A sepan que el turno quedó a la espera.
  - **Conflicto de diseño con A2A**: `system.promt.md` dice explícitamente que el modo A2A
    "nunca pide confirmación" (autonomía total en un solo turno). Este middleware pausaría
    también las llamadas A2A salvo que se desactive específicamente para ese modo — requiere
    decidir si A2A sigue sin confirmar nunca (aceptando el riesgo residual solo ahí) o si
    también cambia esa política, y probablemente dos grafos compilados (uno con el
    middleware para HTTP interactivo, otro sin él para A2A) o contexto por invocación.
- **Mitigación actual, mientras tanto**: guardarraíles de prompt (`system.promt.md`,
  `base.prompt.md`, descripciones de `memory_tools.py`) que reducen la frecuencia del
  problema pero no lo eliminan con garantía — ver la entrada de "guardarraíl contra memoria
  cruzada" más abajo.

---

## 2026-09-16 — feat: turnos concurrentes en HTTP/A2A, configurables por variable de entorno

- **Cambio**: nueva variable `HTTP_ALLOW_CONCURRENT_TURNS` (`Settings`, por defecto
  `True`). En `True` (default) `POST /chat`, `POST /chat/stream` y A2A JSON-RPC
  (`POST /a2a/{assistant_id}`) aceptan turnos concurrentes — antes siempre respondían
  `409` mientras hubiera uno en curso, sin forma de configurarlo. En `False` se
  recupera ese comportamiento original (un run por turno).
- **Por qué es seguro por defecto**: cada turno ya está aislado por su propio
  `chat_id`/`thread_id` en el checkpointer de Postgres, así que correr varios en
  paralelo no mezcla estado entre conversaciones distintas.
- **Implementación**: `AgentState` (`src/http_api/state.py`) pasa de un flag booleano a
  un contador de turnos en curso (`try_begin_task`/`end_task`) con política
  configurable (`allow_concurrent_turns`, fijada en `agent_state` al llamar
  `start_agent`); `GET /status` sigue mostrando `DOING_TASK` mientras haya al menos un
  turno activo y solo vuelve a `UP` cuando termina el último — correcto incluso con
  varios turnos solapados. El chequeo es atómico sin necesidad de `asyncio.Lock`
  porque no hay ningún `await` entre la comprobación y el incremento del contador.
- **Se eliminó** por quedar sin uso: `app.state.agent_lock` (el `asyncio.Lock` que
  antes serializaba la reserva de turno) y `ChatHandler.check_not_busy_or_raise`
  (código muerto, sin ningún llamador).
- **Archivos**: `src/config/settings.py`, `.env.example`, `src/http_api/state.py`,
  `src/http_api/agent_turn_guard.py`, `src/http_api/chat_handler.py`,
  `src/http_api/app.py`, `src/http_api/a2a.py`, `src/http_api/routers/rest_routes.py`,
  `src/commons/agent_http.py`, `test/test_a2a_inbound.py`,
  `test/test_agent_turn_guard.py` (nuevo).

---

## 2026-09-14 — feat: elimina catálogos genéricos ficticios, agrega catch-all real de WO

- **Problema**: `categorias-incidentes.md`/`categorias-requerimientos.md` eran una
  muestra pequeña e ilustrativa del ambiente de pruebas (`CCTI_ARUS.xlsx`), no el
  catálogo real — cualquier caso fuera de los dominios `eventos`/`usuario` se
  categorizaba con datos ficticios.
- **Cambio de diseño confirmado con la mesa de servicio (2026-09-14)**: un caso fuera
  de todo dominio conocido se crea **siempre como Work Order** (nunca como Incidente,
  sin importar si "suena" a algo roto) con esta categorización catch-all fija:
  `Categoria Operacional 1/2 = Gestion de tickets / Acompañamiento`,
  `Categoria de Producto 1/2/3 = Gestion de casos / Control / Casos`. No existe
  catch-all de Incidente.
- **Implementación — el catch-all vive en el skill, no en código/env vars**: se
  descartó a propósito el patrón de `assigned_group` (constante en
  `business_defaults.py` + default de tool parameter). Los `categorization_tier_1/2`/
  `product_cat_tier_1/2/3` de `bmc_create_work_order` siguen siendo **obligatorios**
  (`src/bmc/type_defs/inputs.py`, `src/agent/internal_tools/bmc_tools.py`); el LLM los
  pasa explícitamente leyendo los valores exactos de `guia-creacion-tickets` (sección
  1). Motivo: `skill_get_guide` lee el archivo en vivo en cada llamada, mientras que
  env vars y `system.promt.md` solo se cargan una vez al iniciar el proceso — un
  constante en código habría obligado a reconstruir y reiniciar el agente cada vez que
  la mesa de servicio quiera cambiar esta combinación, cuando basta con editar el
  `.md`. Como `guia-creacion-tickets` ya se lee siempre en todo flujo de creación, no
  cuesta ninguna llamada extra frente a la alternativa de un skill dedicado de 1 fila.
- **Eliminados**: `skills/categorias-incidentes.md`, `skills/categorias-requerimientos.md`.
- **Prompt**: `system.promt.md` y `guia-creacion-tickets/SKILL.md` reescriben el
  protocolo de creación — ya no hay heurístico genérico Incidente-vs-WO ni catálogo
  genérico que consultar; sin dominio conocido, se llama `bmc_create_work_order`
  pasando los valores catch-all documentados en `guia-creacion-tickets`.
- **Test**: `test_bmc_create_work_order_requires_categorization_params_explicitly`
  confirma que esos 5 campos siguen siendo obligatorios en el schema (sin default).

---

## 2026-09-14 — fix: `description` de incidente rechazado por BMC al pasar 100 caracteres

- **Problema confirmado contra BMC real**: `Value does not fall within the limits
  specified for the field(Field ID and Name - HPD:IncidentInterface
  <1000000000 : Description>, Maximum length -100)`. BMC rechaza toda la petición
  (no trunca) cuando `description` supera 100 caracteres — mismo campo AR en
  `bmc_create_incident` (asunto) y `bmc_close_incident` (resumen de cierre).
- **Fix**: nueva constante `INCIDENT_DESCRIPTION_MAX_LENGTH = 100`
  (`src/bmc/libs/constants.py`). `CreateIncidentInput.description` y
  `CloseIncidentInput.description` (`src/bmc/type_defs/inputs.py`) ganan
  `max_length`. Los parámetros `description` de `bmc_create_incident` y
  `bmc_close_incident` (`src/agent/internal_tools/bmc_tools.py`) pasan de `str`
  plano a `Annotated[str, Field(max_length=...)]` — necesario para que el límite
  llegue al schema que ve el LLM (`Field` sin `Annotated` en la firma de la tool no
  sobrevive la reconstrucción del schema de LangChain, mismo hallazgo que el de
  `status`/`Literal` documentado el 2026-07-30).
- **Guía**: `skills/guia-creacion-tickets/SKILL.md` documenta el límite (secciones
  5, 6 y 8) e instruye a resumir en `description` y mover el detalle a
  `detailed_decription` (creación) o `resolution`/una nota (cierre).
- **Sin cambios en `resolution`**: el error de BMC solo mencionó el campo
  `Description`; no se confirmó un límite para `Resolution`, así que no se tocó.

---

## 2026-09-14 — feat: identidad real del solicitante vía CTM:People (`reporter_email`)

- **Problema**: `bmc_create_work_order`/`bmc_create_incident` siempre creaban el ticket a
  nombre de una identidad fija (`BMC_DEFAULT_FIRST_NAME`/`BMC_DEFAULT_LAST_NAME` = "Agentes
  IA"), sin forma de atribuirlo a la persona real que reportó el incidente o solicitó el
  Work Order.
- **Cambio**: nuevo parámetro **obligatorio** `reporter_email` en ambas tools. Antes de
  crear el ticket, se busca ese correo en BMC (`CTM:People`, nuevo
  `BmcClient.search_person_by_email` en `src/bmc/libs/api_client.py`, form
  `BmcSettings.form_people_query` default `CTM:People`) y se usa el `First Name`/`Last
  Name` real encontrado — nunca el fijo. Si no se encuentra a esa persona (o el registro
  tiene el nombre incompleto), **no se crea ningún ticket** y se retorna
  `success: false` con el correo en el mensaje.
- **Desambiguación (`Internet E-mail` no es único en BMC)**: nuevo
  `src/bmc/libs/helpers/person_lookup.py`. Cuando el correo devuelve más de una persona
  (caso real observado: el propio bot de este agente comparte un correo alterno con una
  persona real), se prefiere la coincidencia cuyo `Remedy Login ID` tiene forma de correo
  (contiene `@`) sobre un id tipo bot (`AgentesIA`). Si 0 o 2+ candidatas califican, se usa
  la primera que devuelve BMC (orden no garantizado por la API) y se registra un WARNING —
  la identidad asignada en ese caso puede ser incorrecta; queda documentado explícitamente
  porque puede ser confuso de depurar.
- **`Customer First/Last Name` (Work Order) sin cambios**: siguen fijos por
  `business_defaults.py` — el correo solo resuelve la identidad del *submitter*, no la del
  cliente.
- **Limpieza**: `BMC_DEFAULT_FIRST_NAME`/`BMC_DEFAULT_LAST_NAME` quedaron sin uso (ya nada
  las lee) y se eliminaron de `business_defaults.py`, `.env.example` y `CLAUDE.md`.
- **Riesgo conocido, sin resolver en este cambio**: el `Company` del submitter sigue fijo
  en `ARUS`; si la persona encontrada no pertenece a esa compañía en BMC, el combo
  First+Last+Company podría no calzar con su registro real en `CTM:People` (comportamiento
  de BMC ante eso no ha sido probado).
- **Impacto en el protocolo A2A**: `system.promt.md` ahora exige que el mensaje entrante
  traiga el correo del solicitante; si no lo trae, el agente debe detenerse y reportar el
  error en el resumen estructurado en vez de inventar un correo o crear el ticket con la
  identidad del bot.

---

## 2026-09-14 — feat: nueva tool `get_current_date`

- **Problema**: el agente no tenía forma de saber la fecha/hora real; cualquier razonamiento
  sobre fechas relativas ("hoy", "mañana", "hace dos días") o timestamps escritos en un ticket
  dependía de su conocimiento de entrenamiento, no del reloj real.
- **Cambio**: nueva tool `get_current_date` (`src/agent/internal_tools/datetime_tools.py`),
  registrada en el grafo junto a las demás internal tools (`src/agent/agent.py`,
  `src/agent/internal_tools/__init__.py`). Lee el reloj de sistema del contenedor y lo
  convierte a la zona horaria configurada en `AGENT_TIMEZONE` (nueva variable en
  `src/config/settings.py`, default `America/Bogota`); nombres de día/mes en español via
  tablas fijas, sin depender del locale del SO. Devuelve JSON con fecha corta
  (`DD/MM/YYYY`), día/mes/año/hora por separado, y dos strings combinados listos para citar
  (`short`: "07/10/2026, lunes, octubre"; `long`: "lunes 07 de octubre de 2026").
- **Zona horaria por contenedor**: se agregó `ENV TZ=America/Bogota` a `Dockerfile` y
  `Dockerfile.dev` (reloj del SO), independiente de `AGENT_TIMEZONE` (que controla solo esta
  tool). Se agregó la dependencia `tzdata` (`pyproject.toml`) porque `python:3.12-slim` no
  garantiza tener el paquete de zonas horarias del sistema operativo.
- **Prompt**: `system.promt.md` instruye al agente a usar siempre esta tool para fechas,
  nunca inferirlas de la conversación.

---

## 2026-09-14 — mejora: refuerza la calidad del asunto y la descripción de tickets

- **Problema detectado**: el protocolo de creación de tickets (`system.promt.md`,
  `guia-creacion-tickets`) y el schema de las tools (`inputs.py`, `bmc_tools.py`)
  reforzaban con detalle la categorización (Cat Op/Prod, priority, assigned_group),
  pero el asunto (`summary`/`description`) y la descripción detallada
  (`detailed_description`/`detailed_decription`) solo tenían validación de no-vacío
  (`min_length=1`), sin ninguna guía de contenido — quedaban a criterio libre del LLM.
- **Cambio**: se agregó una sección de criterios de calidad (con ejemplo bueno/malo) a
  `skills/guia-creacion-tickets/SKILL.md` y un ítem al checklist final; se enriquecieron
  los `Field(description=...)` de `CreateWorkOrderInput`/`CreateIncidentInput` en
  `src/bmc/type_defs/inputs.py` y los docstrings NumPy correspondientes en
  `src/agent/internal_tools/bmc_tools.py`, para que el LLM reciba la guía directamente
  en el schema de la tool, no solo en el prompt.
- **Sin cambios de contrato**: mismos nombres, tipos y valores por defecto de los
  parámetros existentes.

---

## 2026-09-11 — fix: corrige grupo inválido de Backup en el catálogo de capacidad

- **`skills/categorias-eventos.md`**: la fila de Backup en la subtabla "Eventos de
  capacidad" (Work Order) apuntaba a `GTI.BACKUP`, un grupo que no existe como tal en
  BMC. Se corrigió a `GTI.BACKUPS`, igual que en la subtabla de disponibilidad
  (Incidente).
- **Contexto**: detectado en la corrida 4 de pruebas end-to-end del fix de grupo de
  Work Order — ese caso puntual quedó reasignado a `SOPORTE MESA DE SERVICIO` pese al
  fix, mientras que una prueba con `GTI.BACKUPS` sí fue respetada por BMC
  (`WO0000000107923`). No es una regresión del fix, sino un dato de catálogo.

---

## 2026-09-11 — fix: BMC ignoraba el `Support Group Name` de work orders sin dos campos adicionales

- **Problema confirmado en Postman**: `WOI:WorkOrderInterface_Create` acepta el POST con
  `Support Group Name` correcto pero BMC no lo respetaba salvo que viajaran junto con él
  dos campos adicionales — mismo síntoma que el fix de incidentes del 2026-09-10, esta
  vez validado directamente contra el formulario de Work Order.
- **Fix**: se envían siempre dos campos fijos junto con `Support Group Name`:
  `Support Company` (`ARUS`) y `Support Organization` (`MAYA`), configurables vía
  `BMC_DEFAULT_WORK_ORDER_SUPPORT_COMPANY` / `BMC_DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION`
  en `business_defaults.py`. Con los tres campos juntos, BMC sí respeta el grupo enviado
  por el caller.
- **Nombres de campo distintos a los de incidente**: el formulario de Work Order usa
  `Support Company`/`Support Organization` (sin el prefijo `Assigned`), a diferencia de
  `Assigned Support Company`/`Assigned Support Organization` en incidentes — confirmado
  en Postman contra ambos formularios.
- **Alcance**: `CreateWorkOrderValues` (`src/bmc/type_defs/ar_values.py`) y la inyección
  en `bmc_create_work_order` (`src/agent/internal_tools/bmc_tools.py`), ya que la
  creación de Work Order no pasa por una clase `WorkOrderOperations.create()` como sí
  ocurre con `IncidentOperations`.
- **Sin cambios de superficie del tool**: los dos campos nuevos son fijos por ambiente,
  igual que en el fix de incidentes — no son parámetros de `bmc_create_work_order`.

---

## 2026-09-10 — fix: BMC ignoraba el `Assigned Group` de incidentes sin dos campos adicionales

- **Problema confirmado en Postman**: `HPD:IncidentInterface_Create` acepta el POST con
  `Assigned Group` correcto (p. ej. `GTI.CLOUD`) pero BMC no lo respeta y reasigna el
  incidente a una cola de asignación por defecto propia de su configuración ITSM (varía
  según la Company del ticket, algo que el agente no controla ni decide) — el incidente
  queda creado pero en la cola equivocada, sin error.
- **Fix**: se envían siempre dos campos fijos junto con `Assigned Group`:
  `Assigned Support Company` (`ARUS`) y `Assigned Support Organization` (`MAYA`),
  configurables vía `BMC_DEFAULT_INCIDENT_SUPPORT_COMPANY` /
  `BMC_DEFAULT_INCIDENT_SUPPORT_ORGANIZATION` en `business_defaults.py`. Con los tres
  campos juntos, BMC sí respeta el grupo enviado por el caller.
- **Alcance solo incidentes**: `CreateWorkOrderValues`, `WorkOrderOperations` y el tool
  `bmc_create_work_order` no se tocan; ese flujo se validará por separado más adelante.
- **Sin cambios de superficie del tool**: los dos campos nuevos son fijos por ambiente,
  igual que `Company`/`First_Name`/`Last_Name` — no son parámetros de
  `bmc_create_incident` porque el catálogo Maya no trae esa información por fila.

---

## 2026-09-07 — feat: Categoría Operacional 1/2/3 para el catálogo de "eventos"

- **`skills/categorias-eventos.md`**: la mesa de servicio entregó las columnas
  `Categoria Operacional 1/2/3` que faltaban para las dos subtablas del dominio
  "eventos". Cierra el vacío documentado en el commit anterior (2026-09-02).
- Ambas subtablas quedan con `Categoria Operacional 1 = Aplicacion` y
  `Categoria Operacional 3` vacía; `Categoria Operacional 2` distingue el tipo de
  evento (`Evento de disponibilidad` en Incidente, `Evento de capacidad` en
  Requerimiento), reforzando la regla semántica ya documentada en la skill.
- Con este dato, `bmc_create_work_order` ya puede categorizar un caso de "eventos de
  capacidad" sin depender de una pregunta adicional al usuario — se retira la
  instrucción de no crear el Work Order sin confirmar antes.
- **Sin cambios de código**: solo se completan filas de la tabla de datos.

---

## 2026-09-02 — feat: catálogo de categorización por dominio ("eventos": disponibilidad vs. capacidad)

- **Nueva skill `skills/categorias-eventos.md`**: catálogo completo (entregado por la
  mesa de servicio) del dominio "eventos" — servicios GTI (AWS, redes, aplicaciones,
  backup, servidores, base de datos, seguridad perimetral, telefonía). Cierra el
  pendiente dejado en el commit d2d29f4 ("cuando también exista el catálogo de
  'eventos'").
- **Dos subtablas en vez de una columna `Tipo Servicio` mezclada** (a diferencia de
  `categorias-usuario`): "Eventos de disponibilidad" (todas `Incidente`) y "Eventos de
  capacidad" (todas `Requerimiento`). La skill documenta la regla semántica que decide
  entre ambas incluso fuera de las filas exactas: disponibilidad = ausencia, caída o
  degradación del servicio (ej. disco lleno, porque hace caer el servicio); capacidad =
  aumento, modificación o adición planeada sobre el servicio (ej. aumentar la capacidad
  de disco).
- **Vacío de datos documentado en su momento**: el catálogo entregado no traía columnas
  de Categoría Operacional 1/2, obligatorias para `bmc_create_work_order`
  (`min_length=1`, `src/bmc/type_defs/inputs.py:49-50`). Resuelto el 2026-09-07 (ver
  entrada de esa fecha).
- **Sin cambios de código**: mismo mecanismo de descubrimiento de skills por
  convención de archivo (`categorias-<dominio>`) usado por `categorias-usuario`.

---

## 2026-09-01 — test: cobertura de `get_huggingface_llm` y temperatura/max_new_tokens configurables

- **`test/test_llm_huggingface.py`** (nuevo): dobles simples (`monkeypatch`) de
  `HuggingFaceEndpoint`/`ChatHuggingFace` — sin conexión real — verifican que
  `HUGGINGFACE_BILL_TO` arma `server_kwargs={"bill_to": ...}` (y `{}` si está vacío),
  que `HUGGINGFACE_PROVIDER` vacío se traduce en `provider=None`, y que
  `_configure_huggingface_legacy_tls()` solo se invoca cuando
  `HUGGINGFACE_ALLOW_LEGACY_TLS=true`.
- **`src/config/settings.py`**: nuevos campos opcionales `llm_temperature` (env
  `LLM_TEMPERATURE`, default `0.6`, compartido por los 4 proveedores) y
  `huggingface_max_new_tokens` (env `HUGGINGFACE_MAX_NEW_TOKENS`, default `2048`).
  Mismos valores que estaban hardcodeados en `src/agent/llm.py`, ahora configurables
  sin cambiar el comportamiento por defecto.
- **`src/agent/llm.py`**: `build_llm` y `get_huggingface_llm` leen esos valores de
  `Settings` en vez de la constante fija.
- **`.env.example`, `CLAUDE.md`**: documentadas las 2 variables nuevas.
- **`test/test_settings_multiinstance.py`**: test de default/override para ambos
  campos.
- **Motivación**: auditoría cruzada desde otra sesión (portando el mismo soporte HF en
  `knowledge-agent`) señaló que el commit 939231f de esta rama tenía cobertura de tests
  delgada para `get_huggingface_llm` y valores de temperatura/tokens fijos sin punto de
  configuración.

---

## 2026-09-01 — refactor: consolida procedimiento de categorización en `guia-creacion-tickets` (sin duplicación entre skills)

- **`skills/guia-creacion-tickets/SKILL.md`** pasa a ser la única fuente del: mapeo
  columna → parámetro (una tabla por concepto, válida para `bmc_create_work_order` y
  `bmc_create_incident`), la traducción de Prioridad ES→EN, el significado de columnas
  informativas de catálogos de dominio (`¿Susceptible de cierre en mesa?`) y qué hacer
  si un caso no encaja en ninguna fila.
- **`skills/categorias-incidentes.md`, `skills/categorias-requerimientos.md`,
  `skills/categorias-usuario.md`**: recortadas a solo su tabla de datos + una línea de
  contexto que remite a `guia-creacion-tickets` — ya no repiten el mapeo, la traducción
  de prioridad ni el texto de fallback.
- **Motivación**: al revisar el commit anterior se notó que cada skill de
  categorización repetía el mismo procedimiento (mapeo, prioridad, "no inventes"), y
  que `categorias-usuario.md` en particular traía información de proceso que no le
  correspondía — debía limitarse a los casos que atiende y su tipificación.
- **Balance medido**: la suma de las 4 skills bajó ~22% (20 180 → 15 673 bytes). Un
  turno con dominio conocido (`categorias-usuario`) bajó ~15%; un turno genérico sin
  dominio (`categorias-incidentes`/`categorias-requerimientos`) subió ligeramente
  (~600 bytes) porque `guia-creacion-tickets` — que se lee siempre — creció al asumir
  el mapeo consolidado. El ahorro compuesto crece con cada dominio nuevo que se agregue
  (`categorias-eventos`, etc.), que ya no necesita repetir ese procedimiento.
- **Sin cambios de comportamiento ni de código**: mismos datos de categorización,
  mismo protocolo en `system.promt.md`; solo se reorganizó dónde vive cada pieza de
  información.

---

## 2026-09-01 — feat: soporte de inferencia vía Hugging Face Inference Providers

- **`LLM_PROVIDER=huggingface`** como opción nueva de proveedor, junto a `ollama`,
  `openai` y `anthropic` (`src/config/settings.py`). Requiere `HUGGINGFACE_API_KEY` y
  `HUGGINGFACE_MODEL` (validado en `Settings`).
- **`src/agent/llm.py`**: `get_huggingface_llm()` construye un `ChatHuggingFace` sobre
  `HuggingFaceEndpoint` (`langchain-huggingface`), enrutando por
  `https://router.huggingface.co` (HF Inference Providers). Soporta `HUGGINGFACE_PROVIDER`
  (proveedor detrás del router, ej. `together`/`novita`/`cerebras`) y
  `HUGGINGFACE_BILL_TO` (organización a la que facturar).
- **`HUGGINGFACE_ALLOW_LEGACY_TLS`** (solo dev): relaja `SECLEVEL` de OpenSSL para el
  cliente HTTP de `huggingface_hub` en redes corporativas con inspección TLS cuyo CA
  raíz usa clave débil o firma SHA-1; la verificación de certificado sigue activa.
  Nunca debe activarse en producción.
- **Riesgo a tener en cuenta**: el tool calling con modelos servidos vía HF **no está
  garantizado** — depende del modelo/proveedor elegido, a diferencia de OpenAI/Anthropic.
  Este agente depende de tool calling para todas sus operaciones (BMC, memoria, skills),
  así que hay que validar explícitamente el modelo elegido antes de usarlo en producción.
- **Dependencia nueva**: `langchain-huggingface==1.2.2` (`pyproject.toml`, `uv.lock`).
- **`.env.example` y `CLAUDE.md`**: documentadas las nuevas variables de entorno.
- **Test**: `test/test_settings_multiinstance.py::test_huggingface_provider_requires_api_key_and_model`.

---

## 2026-09-01 — feat: catálogo de categorización por dominio ("usuario de red") y el catálogo de dominio decide Incidente vs Work Order

- **Nueva skill `skills/categorias-usuario.md`**: catálogo completo (entregado por la
  mesa de servicio, no una muestra) de categorización del dominio "usuario de red"
  (altas/bajas de usuario, contraseñas, estado de casos). A diferencia de
  `categorias-incidentes`/`categorias-requerimientos` (separadas por tipo), esta tabla
  trae una columna **`Tipo Servicio`** por fila que decide si el ticket es Incidente o
  Work Order, más `Escalamiento 1` (mapea a `assigned_group`) y
  `¿Susceptible de cierre en mesa?` (documentada como informativa, sin regla dura de
  auto-cierre).
- **Motivación del reordenamiento**: se depuró un caso real ("desbloqueo de usuario")
  donde el LLM decidió el tipo de ticket con el heurístico genérico de
  `guia-creacion-tickets` (semántico: "roto" → Incidente) y nunca llegó a revisar el
  catálogo de dominio, que ya tenía una fila exacta clasificada como Work Order — pese a
  que el system prompt cargado sí incluía la skill (confirmado en
  `logs/agent_agent_bmc.log`). La causa era de **orden/precedencia**, no de código.
- **`system.promt.md`**: el protocolo de creación ahora busca primero un dominio
  conocido (stem `categorias-<dominio>`, patrón genérico — no
  `categorias-requerimientos-<dominio>`); si una fila de esa tabla aplica, su
  `Tipo Servicio` decide el tipo y **tiene prioridad** sobre el heurístico genérico de
  `guia-creacion-tickets`, que pasa a ser el *fallback* cuando no hay match de dominio.
  Los flujos de ejemplo (interactivo y A2A) se reescribieron para reflejar este orden.
- **`skills/guia-creacion-tickets/SKILL.md`**: la sección "Work Order vs Incidente" y
  el checklist final ahora anteponen la columna `Tipo Servicio` del catálogo de dominio
  al heurístico semántico.
- **Asimetría documentada en la skill de dominio**: `bmc_create_incident` no recibe
  `priority` (Impact/Urgency quedan fijos) — si `Tipo Servicio = Incidente`, la columna
  Prioridad de la fila se ignora; y `product_cat_tier_*` (Work Order) vs
  `product_categorization_tier_*` (Incidente) son nombres de parámetro distintos para
  el mismo dato de la tabla.
- **Sin cambios de código**: `bmc_tools.py`, `constants.py`, `business_defaults.py` y
  el mecanismo de descubrimiento de skills (`src/config/skill_catalog.py`) ya soportan
  esto sin modificación — el catálogo de skills se descubre por convención de archivo,
  no por registro manual.
- **Acción operativa**: tras este cambio hay que reconstruir el agente
  (`build_agent` / reinicio del proceso, o `POST /stop` + `POST /start` en HTTP) para
  que el bloque `<skills>` del system prompt refleje el stem `categorias-usuario` (ya
  no `categorias-requerimientos-usuario`).
- **Fuera de alcance de este cambio**: no se diseñó todavía la "especialización" del
  agente por dominio a nivel de arquitectura (multi-instancia u orquestador) ni se
  codificó ninguna regla dura de auto-cierre — quedan para un cambio posterior, cuando
  también exista el catálogo de "eventos".

---

## 2026-07-30 — fix: completa la sincronización con bmc-mcp (grupo asignado en WO y enum de Status)

- **`bmc_create_work_order`** ganó el parámetro `assigned_group` (default
  `BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP`, fallback `MESA MARCO`), igual que ya tenía
  `bmc_create_incident`. `CreateWorkOrderValues`/`CreateWorkOrderInput` agregan el campo
  (`Support Group Name`). Antes del fix la WO se creaba sin grupo de soporte pese a que
  `system.promt.md` y `skills/guia-creacion-tickets/SKILL.md` ya instruían al LLM a
  extraerlo del catálogo — quedaba huérfano de cola de atención en BMC.
- **`src/bmc/libs/business_defaults.py`**: nueva constante
  `DEFAULT_WORK_ORDER_ASSIGNED_GROUP` (env `BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP`).
- **`status` ahora se expone como enum real al LLM** en `bmc_create_work_order`,
  `bmc_update_work_order_status` y `bmc_create_incident`: se cambió el tipo del
  parámetro de `str` a `Literal[...]` (sobre `WORK_ORDER_STATUSES`/`INCIDENT_STATUSES`).
  El intento previo con `Field(json_schema_extra={'enum': ...})` no llegaba al schema
  visible por el modelo — `langchain_core` reconstruye el `FieldInfo` del `args_schema`
  al armar el `tool_call_schema` (`_create_subset_model_v2`) sin copiar
  `json_schema_extra`; `Literal` sí sobrevive esa reconstrucción porque queda en la
  anotación del campo, no en sus metadatos.
- **`system.promt.md`** y **`skills/categorias-requerimientos.md`**: el flujo de
  creación de Work Order y la tabla de mapeo de columnas ahora incluyen
  `assigned_group` ↔ `Grupo (referencia)`.
- **`.env.example`** y **`CLAUDE.md`**: documentada la nueva variable
  `BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP`.
- **Motivación**: auditoría de la sincronización 2026-07-29 con `bmc-mcp` (ver entrada
  siguiente) detectó estos dos huecos: `assigned_group` faltante en WO (severidad alta,
  riesgo operativo real) y el enum de `Status` no reflejado en el schema expuesto al LLM
  (severidad media, riesgo de alucinación de valores inválidos).

---

## 2026-07-29 — feat: sincroniza la capa BMC del agente con el contrato actual de bmc-mcp

- **Renombradas las 12 tools internas** en `src/agent/internal_tools/bmc_tools.py` con prefijo
  `bmc_*` (`bmc_create_work_order`, `bmc_close_incident`, etc.), igualando el namespacing del
  servidor MCP. `system.promt.md`, `README.md`, `CLAUDE.md` y `docs/ARCHITECTURE.md` actualizados.
- **`src/bmc/libs/helpers/ticket_guards.py`** (nuevo, portado de `bmc-mcp`): `require_not_closed`
  rechaza cualquier escritura sobre un ticket ya `Closed`; `require_submitter` (solo cierre) rechaza
  cerrar un ticket cuyo `Submitter` no coincide con `BMC_USERNAME`. Aplicados en
  `work_order_operations.py` e `incident_operations.py`.
- **Corregido bug de formulario**: `bmc_add_incident_note`/`bmc_add_incident_attachment` escribían
  contra `WOI:WorkInfo` (formulario de Work Order); ahora usan el método nuevo
  `BmcClient.post_incident_work_log` contra `HPD:WorkLog` (`BMC_FORM_INCIDENT_WORK_LOG`).
- **`bmc_close_work_order`** reescrito a 3 PUT (toma de propiedad con `ASCHG` sin nota → `Completed`
  + nota → `Closed` + nota), sin exigir `In Progress` previo; elimina los parámetros obsoletos
  `description`, `final_status`, `status_reason`.
- **`bmc_close_incident`** reescrito a 2 PUT (toma de propiedad con `Assignee` → `Resolved` con
  `Status_Reason='Closing'` fijo); elimina los parámetros obsoletos `intermediate_description`,
  `intermediate_status`, `final_status`, `status_reason`.
- **`bmc_create_incident`**: `impact`/`urgency` dejan de ser parámetros (fijos en
  `INCIDENT_FIXED_IMPACT`/`INCIDENT_FIXED_URGENCY`, igual que en bmc-mcp); se agrega el parámetro
  `assigned_group` (antes constante fija `MESA MARCO` sin relación con la categoría; ahora el LLM
  lo completa desde la fila elegida en `categorias-incidentes`, con ese mismo valor como default
  de emergencia).
- **Portado el workaround de categorización vacía** (`IncidentOperations.create`): si BMC deja
  `Categorization Tier 1/2` vacío tras crear el incidente pese a una combinación de categoría
  válida, aplica un PUT de corrección best-effort y deja nota en el work log.
- **`src/bmc/config/settings.py`**: agrega `assignee_display_name` (obligatorio, usado en
  `ASCHG`/`Assignee` al tomar propiedad antes de cerrar) y `form_incident_work_log`.
- **Skills de categorización actualizadas** (`skills/categorias-incidentes.md`,
  `skills/categorias-requerimientos.md`): reemplazado su contenido por una muestra pequeña y
  curada (no el catálogo completo de ~1900 combinaciones de `bmc-mcp/config/categorias_maya.json`,
  que excede el límite de lectura de `skill_get_guide` de 12 000 caracteres) enfocada en escenarios
  comunes de un área de TI (usuarios/telefonía, cambio de contraseña, caída de aplicaciones).
- **Nuevo skill `skills/guia-creacion-tickets/SKILL.md`**: guía de proceso (Work Order vs
  Incidente, regla de una única fila de categorización, campos fijados por el entorno, guards de
  negocio, modo A2A).
- **Fuera de alcance deliberadamente**: no se portó un catálogo de categorías estructurado (JSON)
  ni una tool de búsqueda de categorías — el mecanismo de categorización sigue siendo Markdown
  leído por el LLM, por decisión explícita para este agente.
- **Motivación**: la capa BMC del agente era una copia congelada del 2026-06-25 de `bmc-mcp`, que
  desde entonces incorporó guards de negocio, patrón de toma de propiedad en cierre, y corrigió el
  bug de formulario de notas de incidente. El objetivo es que el agente replique ese comportamiento
  manteniendo su arquitectura de tools internas (sin conectarse a un MCP real).

---

## 2026-06-26 — feat: valores de negocio quemados y categorización opcional en incidentes

- **`src/bmc/libs/business_defaults.py`** (nuevo): constantes de negocio con fallback a variables
  de entorno (`BMC_DEFAULT_COMPANY`, `BMC_DEFAULT_FIRST_NAME`, `BMC_DEFAULT_LAST_NAME`,
  `BMC_DEFAULT_CUSTOMER_FIRST_NAME`, `BMC_DEFAULT_CUSTOMER_LAST_NAME`, `BMC_DEFAULT_CUSTOMER_COMPANY`,
  `BMC_DEFAULT_ASSIGNED_GROUP`). Valor hardcoded si la variable no está inyectada.
- **`src/agent/internal_tools/bmc_tools.py`**: eliminados de la firma `@tool` de `create_work_order`
  los parámetros `company`, `first_name`, `last_name`, `customer_first_name`, `customer_last_name`,
  `customer_company`; y de `create_incident` los parámetros `company`, `first_name`, `last_name`,
  `assigned_group`. Los valores se inyectan directamente desde `business_defaults` al construir
  `CreateWorkOrderValues` / `CreateIncidentValues`, sin pasar por el input del LLM.
- **`src/bmc/type_defs/inputs.py`**: `CreateWorkOrderInput` y `CreateIncidentInput` eliminan los
  campos quemados; `categorization_tier_1` y `categorization_tier_2` en `CreateIncidentInput`
  pasan a ser opcionales con default `''`.
- **`src/bmc/type_defs/ar_values.py`**: `CreateIncidentValues.categorization_tier_1/2` con
  `default=''` para que se envíen como string vacío a BMC (compatibilidad probada).
- **`.env.example`** y **`CLAUDE.md`**: documentadas las 7 nuevas variables de entorno.
- **Motivación**: el LLM rellenaba los campos de empresa/solicitante con el texto del mensaje del
  usuario (e.g. "Arus S.A.S." en vez de "ARUS"), causando error 400 en BMC (`$MENU$` no válido).
  Al sacarlos del schema de la tool, el LLM ya no puede sobreescribirlos.

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
