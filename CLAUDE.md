# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

**agent-bmc** is a LangGraph-based AI agent for managing **incidents** and **work orders** in
**BMC Helix ARUS**. It is built on top of `agent_forge` — a production-ready Python framework for
conversational agents — and extends it with 14 internal LangChain tools that wrap the BMC Helix
AR REST API directly (no MCP server required).

---

## Table of Contents

1. [Purpose](#purpose)
2. [Project Structure](#project-structure)
3. [High-Level Architecture](#high-level-architecture)
4. [Tech Stack](#tech-stack)
5. [Build, Test and Run](#build-test-and-run)
6. [Configuration](#configuration)
7. [BMC Internal Tools](#bmc-internal-tools)
8. [Adding New BMC Tools](#adding-new-bmc-tools)
9. [HTTP API](#http-api)
10. [Database and Persistence](#database-and-persistence)
11. [Agent Memory and Skills](#agent-memory-and-skills)
12. [Turn Lifecycle](#turn-lifecycle)

---

## Purpose

`agent-bmc` provides a conversational AI agent that can:

- **Create, query and update** incidents (`INC`) and work orders (`WO`) in BMC Helix ARUS.
- **Add notes and attachments** to existing tickets via `WOI:WorkInfo`.
- **Close tickets** following BMC's two-step flow (intermediate PUT → final PUT).
- **Verify the BMC session** at any time via `bmc_health_check`.
- Persist conversation history in PostgreSQL via LangGraph checkpointer.
- Expose a REST API (FastAPI) and an interactive CLI (REPL).

---

## Project Structure

```
agent-bmc/
├── src/
│   ├── agent/                        # LangGraph agent core
│   │   ├── agent.py                  # build_agent(): BMC lifecycle + graph compilation
│   │   ├── llm.py                    # LLM factory (Ollama / OpenAI / Anthropic)
│   │   ├── mcp_tools.py              # Optional extra MCP tools via MCP_URLS
│   │   ├── cli.py                    # Interactive REPL
│   │   ├── prompts.py                # System prompt loader (Langfuse / file)
│   │   ├── a2a_peers.py              # Outbound A2A client
│   │   ├── tool_error_policy.py      # Global tool error handling
│   │   ├── interceptors/             # LLM/tool event callbacks
│   │   └── internal_tools/
│   │       ├── bmc_tools.py          # bmc_health_check + registry (get_bmc_tools(), _ALL_BMC_TOOLS)
│   │       ├── bmc_work_order_tools.py  # 7 Work Order @tool functions
│   │       ├── bmc_incident_tools.py    # 6 Incident @tool functions
│   │       ├── memory_tools.py       # memory_* tools (chat/run history)
│   │       ├── skill_tools.py        # skill_get_guide
│   │       ├── datetime_tools.py     # get_current_date (system clock, AGENT_TIMEZONE)
│   │       └── a2a_tools.py          # a2a_list_remote_agents, a2a_send_to_remote
│   ├── bmc/                          # BMC Helix client layer
│   │   ├── config/settings.py        # BmcSettings (BMC_BASE_URL, BMC_USERNAME, …)
│   │   ├── exceptions/mcp.py         # MCPClientError, MCPLoginError, MCPValidationError
│   │   ├── libs/
│   │   │   ├── connection_manager.py # Singleton JWT session + auto-refresh
│   │   │   ├── api_client.py         # BmcClient: async HTTP methods per AR form
│   │   │   ├── tool_handler.py       # BaseToolHandler: shared write guard + TOON encode
│   │   │   ├── constants.py          # AR field names, status catalogs, error messages
│   │   │   ├── toon_encoder.py       # TOON response encoder
│   │   │   └── helpers/
│   │   │       ├── ar_query_builder.py
│   │   │       ├── entry_values_mapper.py
│   │   │       ├── guarded_write.py       # run_guarded_write: shared guard skeleton for ticket writes
│   │   │       ├── multipart_builder.py
│   │   │       ├── work_order_operations.py
│   │   │       ├── incident_operations.py
│   │   │       └── person_lookup.py       # CTM:People reporter identity resolution
│   │   └── type_defs/                # Pydantic models for BMC inputs/outputs
│   │       ├── inputs.py             # CreateWorkOrderInput, CreateIncidentInput, …
│   │       ├── outputs.py            # BaseOutput, WorkOrderCreatedData, …
│   │       ├── ar_values.py          # AR field aliases (CreateWorkOrderValues, …)
│   │       ├── ar_api.py             # BmcEntryListResponse, BmcCreateEntryResponse
│   │       ├── ticket_status.py      # WorkOrderStatus, IncidentStatus enums
│   │       └── json_types.py         # JsonValue alias
│   ├── config/                       # Agent settings (LLM, DB, A2A, Langfuse)
│   ├── http_api/                     # FastAPI service
│   ├── commons/                      # Shared runner, A2A inbound, utils
│   ├── database/                     # Checkpointer, store, models
│   ├── services/                     # Chat, run and event services
│   ├── exception/                    # Domain exceptions
│   └── type_defs/                    # HTTP contract types (Pydantic + TypedDict)
├── skills/                           # Local Markdown skill guides
├── docs/                             # Technical documentation
├── test/                             # Tests (pytest + integration)
├── alembic/                          # DB migrations
├── pyproject.toml
├── .env.example
├── system.promt.md                   # BMC-specific system prompt
└── base.prompt.md                    # Memory and skills base prompt
```

---

## High-Level Architecture

```
User (CLI / HTTP)
        │
   AgentRunner.run_agent_turn()
        │
   LangGraph graph.ainvoke()
        ├─ LLM (Ollama / OpenAI / Anthropic)
        ├─ Internal tools
        │   ├─ memory_*         (chat/run history)
        │   ├─ skill_get_guide  (Markdown guides)
        │   ├─ get_current_date (system clock, AGENT_TIMEZONE)
        │   ├─ BMC tools        (15 tools → BmcClient → BMC Helix REST)
        │   └─ a2a_*            (remote agents, optional)
        └─ MCP tools (optional, from MCP_URLS)

BmcClient ──► BmcConnectionManager (JWT singleton, auto-refresh)
                        │
                 BMC Helix AR REST API
                  (arus-dev-restapi.onbmc.com)
```

### BMC session lifecycle

`build_agent()` in `src/agent/agent.py`:
1. If `BMC_BASE_URL` is set → instantiate `BmcConnectionManager`, call `start()` (login + refresh loop).
2. Call `get_bmc_tools()` → lazy `BaseToolHandler` initialization.
3. Build LangGraph with all tools.
4. On exit → `BmcConnectionManager.stop()` cancels the refresh task and closes the HTTP client.

If `BMC_BASE_URL` is **not** set, BMC tools return an empty list and the agent starts without them
(useful for development without BMC access).

---

## Tech Stack

| Layer | Library | Version |
|-------|---------|---------|
| Agent framework | LangChain + LangGraph | 1.2.15 / 1.1.6 |
| LLM providers | langchain-anthropic / openai / ollama | latest |
| HTTP client (BMC) | httpx | 0.28.1 |
| Output encoding | toon-formatter | 1.0.1 |
| Validation | Pydantic + pydantic-settings | 2.13.1 |
| Persistence | PostgreSQL + asyncpg + SQLAlchemy | — |
| LangGraph checkpointer | langgraph-checkpoint-postgres | 3.0.5 |
| HTTP server | FastAPI + Uvicorn | 0.136.0 |
| Observability | Langfuse (optional) | 4.6.1 |
| Package manager | uv | — |

---

## Build, Test and Run

```bash
# Install dependencies
uv sync

# Install with dev tools
uv sync --group dev

# Lint
uv run ruff check src/
uv run pylint src/
uv run mypy                 # tipado estático; config en mypy.ini; debe quedar en 0 errores

# Run tests (unit only, no BMC or Postgres required)
uv run pytest test/test_fake_llm_tool_flow.py test/test_skill_catalog.py -v

# Run all tests (requires Postgres)
uv run pytest test/ -v

# Start CLI (REPL)
uv run agente

# Start HTTP server (dev with autoreload)
uv run uvicorn http_api.app:app --reload --port 8000

# Start HTTP server (production)
uv run agent-bmc-http
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the required values.

### Required — BMC Helix

| Variable | Description |
|----------|-------------|
| `BMC_BASE_URL` | BMC REST API base URL (e.g. `https://arus-dev-restapi.onbmc.com`) |
| `BMC_USERNAME` | Service account email; also compared against a ticket's `Submitter` by the `require_submitter` close guard |
| `BMC_PASSWORD` | Service account password / API key |
| `BMC_ASSIGNEE_DISPLAY_NAME` | Display name used for `ASCHG` (WO) / `Assignee` (incident) when taking ownership before closing; distinct from `BMC_USERNAME` |

### Optional — BMC

| Variable | Default | Description |
|----------|---------|-------------|
| `BMC_ALLOW_WRITE` | `true` | Enable CREATE/UPDATE/CLOSE operations |
| `BMC_JWT_TTL_SECONDS` | `3600` | JWT lifetime in seconds |
| `BMC_JWT_REFRESH_MARGIN_SECONDS` | `300` | Refresh JWT this many seconds before expiry |
| `BMC_HTTP_TIMEOUT_SECONDS` | `30.0` | HTTP timeout toward BMC |
| `BMC_MAX_ATTACHMENT_BYTES` | `10485760` | Max attachment size (10 MiB) |
| `BMC_ATTACHMENT_BASE_DIR` | (none) | Only folder files can be attached from; unset disables attachments (path traversal/symlinks are rejected) |

### Business defaults — BMC tickets

Fixed values injected by `src/bmc/libs/business_defaults.py` into every `bmc_create_work_order`
and `bmc_create_incident` call. The LLM never sees these as tool parameters. The submitter's
`First Name`/`Last Name` are **not** in this table — they are resolved per-call from
`reporter_email` (see "Reporter identity resolution" above), not a fixed default.

| Variable | Fallback | Used in |
|----------|----------|---------|
| `BMC_DEFAULT_COMPANY` | `ARUS` | WO + incident `Company` |
| `BMC_DEFAULT_CUSTOMER_FIRST_NAME` | `Mosaico` | WO `Customer First Name` |
| `BMC_DEFAULT_CUSTOMER_LAST_NAME` | `WebServices` | WO `Customer Last Name` |
| `BMC_DEFAULT_CUSTOMER_COMPANY` | `ARUS` | WO `Customer Company` |
| `BMC_DEFAULT_ASSIGNED_GROUP` | `MESA MARCO` | Default of the `assigned_group` **tool parameter** of `bmc_create_incident` (not a fixed injection — the LLM should override it with the value from a matching `categorias-<dominio>` skill row, e.g. `categorias-eventos`/`categorias-usuario`) |
| `BMC_DEFAULT_INCIDENT_SUPPORT_COMPANY` | `ARUS` | Fixed incident `Assigned Support Company`, required alongside `Assigned Support Organization` for BMC to honor the `Assigned Group` sent by the caller (otherwise BMC silently reassigns the incident per its own ITSM configuration) |
| `BMC_DEFAULT_INCIDENT_SUPPORT_ORGANIZATION` | `MAYA` | Fixed incident `Assigned Support Organization` — see `BMC_DEFAULT_INCIDENT_SUPPORT_COMPANY` |
| `BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP` | `MESA MARCO` | Default of the `assigned_group` **tool parameter** of `bmc_create_work_order` — the LLM should override it with the value from a matching `categorias-<dominio>` skill row when one applies; otherwise (no known domain) this default is the correct, confirmed value, not a placeholder |
| `BMC_DEFAULT_WORK_ORDER_SUPPORT_COMPANY` | `ARUS` | Fixed work order `Support Company`, required alongside `Support Organization` for BMC to honor the `Support Group Name` sent by the caller (otherwise BMC silently reassigns the work order per its own ITSM configuration) |
| `BMC_DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION` | `MAYA` | Fixed work order `Support Organization` — see `BMC_DEFAULT_WORK_ORDER_SUPPORT_COMPANY` |

### Required — LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `openai` \| `anthropic` \| `huggingface` |
| `LLM_TEMPERATURE` | `0.6` | Sampling temperature shared by all 4 providers |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Model name when using Ollama |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `HUGGINGFACE_API_KEY` | — | Required when `LLM_PROVIDER=huggingface` |
| `HUGGINGFACE_MODEL` | — | Required when `LLM_PROVIDER=huggingface`; repo id routed through HF Inference Providers (e.g. `meta-llama/Llama-3.3-70B-Instruct`). Must support tool calling — not guaranteed for every model |
| `HUGGINGFACE_PROVIDER` | `auto` | Optional underlying inference provider behind the HF router (e.g. `together`, `novita`, `cerebras`) |
| `HUGGINGFACE_BILL_TO` | — | Optional HF organization to bill inference to (`InferenceClient(bill_to=...)`); empty bills the token's own account |
| `HUGGINGFACE_MAX_NEW_TOKENS` | `2048` | Output token limit for the HF endpoint |
| `HUGGINGFACE_ALLOW_LEGACY_TLS` | `false` | **Dev-only.** Relaxes OpenSSL's security level (`SECLEVEL=1`) for `huggingface_hub`'s HTTP client, to accept a corporate TLS-inspection root CA with a weak key (<2048-bit RSA) or SHA-1 signature. Certificate verification stays on; requires `SSL_CERT_FILE` pointing to a bundle that trusts that CA. Never enable in production — fix is reissuing the CA with a modern key |

### Required — Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/agent_bmc` | Postgres DSN |

### Agent identity

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_SLUG` | `agent_bmc` | Unique identifier (pattern `^[a-z][a-z0-9_]*$`) |
| `AGENT_TIMEZONE` | `America/Bogota` | IANA timezone (`zoneinfo` name) used by the `get_current_date` tool; independent of the container OS's `TZ` |

### System prompt precedence

1. `SYSTEM_PROMPT` (inline env var) — highest priority
2. `LANGFUSE_PROMPT_NAME` (if all Langfuse vars are set)
3. `SYSTEM_PROMPT_PATH` (file path)
4. `system.promt.md` in the repo root — default (BMC-specific)

---

## BMC Internal Tools

The 15 tools are split across `bmc_tools.py` (`bmc_health_check` + the registry),
`bmc_work_order_tools.py` (Work Orders), `bmc_incident_tools.py` (Incidents) and
`bmc_staged_files_tools.py` (files staged by another agent) — split
once the original single file grew past the repo's 1000-line-per-module limit. All four
share one lazy `BaseToolHandler` singleton via `bmc.libs.tool_handler.get_shared_handler()`,
deliberately *not* imported between the agent-side modules, to avoid a cyclic import
between the aggregator (`bmc_tools.py`) and the modules it registers.

| Tool | Operation | AR Form |
|------|-----------|---------|
| `bmc_health_check` | Verify JWT session | GET ping |
| `bmc_create_work_order` | Create WO; `reporter_email` required, resolves submitter First/Last Name via `CTM:People` (rejects with no WO created if not found) | `WOI:WorkOrderInterface_Create` |
| `bmc_get_work_order` | Search WO by ID; returns only title/status/assigned group — never the detailed description, notes or other raw BMC fields (privacy) | `WOI:WorkOrderInterface` |
| `bmc_list_work_orders_by_email` | List WOs by requester email (`Customer Internet E-mail`, the raw `reporter_email` used at creation — not the `CTM:People`-resolved login id); same lean fields as `bmc_get_work_order`, capped at `MAX_TICKETS_BY_EMAIL_RESULTS` | `WOI:WorkOrderInterface` |
| `bmc_add_work_order_note` | Add note without attachment (rejects if `Closed`) | `WOI:WorkInfo` |
| `bmc_add_work_order_attachment` | Add note with file attachment (rejects if `Closed`) | `WOI:WorkInfo` multipart |
| `bmc_update_work_order_status` | PUT intermediate status (rejects if `Closed`) | `WOI:WorkOrderInterface` |
| `bmc_close_work_order` | Ownership PUT (`ASCHG`) → Completed PUT+note → Closed PUT+note (rejects if `Closed` or not opened by `BMC_USERNAME`) | `WOI:WorkOrderInterface` + `WOI:WorkInfo` |
| `bmc_create_incident` | Create incident (Impact/Urgency fixed; `assigned_group` is a tool parameter); `reporter_email` required, resolves submitter First/Last Name via `CTM:People` (rejects with no incident created if not found) | `HPD:IncidentInterface_Create` |
| `bmc_get_incident` | Search incident by number; returns only title/status/assigned group — never the detailed description, notes or other raw BMC fields (privacy) | `HPD:IncidentInterface` |
| `bmc_list_incidents_by_email` | List incidents by requester email (`Internet E-mail`, the raw `reporter_email` used at creation — not the `CTM:People`-resolved login id); same lean fields as `bmc_get_incident`, capped at `MAX_TICKETS_BY_EMAIL_RESULTS` | `HPD:IncidentInterface` |
| `bmc_add_incident_note` | Add note without attachment (rejects if `Closed`) | `HPD:WorkLog` |
| `bmc_add_incident_attachment` | Add note with file attachment (rejects if `Closed`) | `HPD:WorkLog` multipart |
| `bmc_attach_staged_files` | Upload every file listed in `<BMC_ATTACHMENT_BASE_DIR>/<staging_id>/manifest.json` to an Incident or WO (one work log entry each); over-limit/missing files are skipped and listed in one note. Takes only a `staging_id`, never paths or bytes | `HPD:WorkLog` / `WOI:WorkInfo` multipart |
| `bmc_close_incident` | Ownership PUT (`Assignee`) → Resolved PUT with `Status_Reason=Closing` (rejects if `Closed` or not opened by `BMC_USERNAME`) | `HPD:IncidentInterface` |

All tools return a JSON string with `{"success": bool, "message": "..."}`. On success, `message`
contains TOON-encoded structured data. On error, `message` contains a user-facing Spanish error.

Business-rule guards (`src/bmc/libs/helpers/ticket_guards.py`) run before any write: `require_not_closed`
rejects writes on tickets already `Closed`; `require_submitter` (close only) rejects closing a ticket
whose `Submitter` does not match `BMC_USERNAME` — adding notes/attachments to such a ticket is still
allowed. The common write skeleton is `run_guarded_write` in `helpers/guarded_write.py` (both
`*Operations` classes use it; `require_submitter` is passed as `extra_guard` by the close flows).

### Reporter identity resolution (`bmc_create_work_order` / `bmc_create_incident`)

BMC's create forms have no "create from just an email" field — `First Name`/`Last Name`
(submitter identity, distinct from the fixed `Customer` identity) must be sent as free text.
`src/bmc/libs/helpers/person_lookup.py` resolves them from the required `reporter_email`
parameter by querying `CTM:People` (`BmcClient.search_person_by_email`, form
`BmcSettings.form_people_query`, default `CTM:People`) instead of a fixed persona. If no
person is found (or the matched record has an incomplete name), the call fails with no
ticket created — it never falls back to a fixed identity. `Internet E-mail` is **not** a
unique key in BMC: when more than one person shares the email, the entry whose `Remedy
Login ID` looks like a real email (contains `@`) wins over a bot-style id (observed in
practice: this agent's own bot identity can share an email with a real person); if zero or
several candidates qualify, the first entry BMC returns is used and a WARNING is logged,
since BMC's result order for a non-unique match is not guaranteed.

---

## Adding New BMC Tools

1. Add input/output models to `src/bmc/type_defs/inputs.py` and `outputs.py` if needed.
2. Add AR field constants to `src/bmc/libs/constants.py` if needed.
3. Add the HTTP method to `src/bmc/libs/api_client.py`.
4. Add a helper in `src/bmc/libs/helpers/` if the operation has multiple steps.
5. Add the `@tool` function to `bmc_work_order_tools.py` or `bmc_incident_tools.py`
   (whichever ticket type it's for), following the lazy handler pattern
   (`handler = tool_handler.get_shared_handler()`). Pass an explicit, concise
   `@tool(description=...)` for the LLM — see "Docstring de humanos vs. descripción de
   tool para el LLM" in `.claude/rules/estandar-python.md`; don't rely on the bare
   `@tool` decorator falling back to the (human-facing) docstring.
6. Register it in the `_ALL_BMC_TOOLS` list and import it, both in `bmc_tools.py`.
7. Document it in this file and in `README.md`.

---

## HTTP API

Same endpoints as agent_forge. Key routes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Agent status |
| `POST` | `/chat` | Single-turn chat (blocking) |
| `POST` | `/chat/stream` | Streaming chat (SSE) |
| `GET` | `/chats` | List chats |
| `GET` | `/runs/last` | Last run detail |
| `GET` | `/runs/stats` | Run statistics |
| `POST` | `/start` | Start agent (HTTP mode) |
| `POST` | `/stop` | Stop agent (HTTP mode) |
| `GET` | `/.well-known/agent-card.json` | A2A Agent Card |
| `POST` | `/a2a` | A2A inbound (JSON-RPC) |

---

## Database and Persistence

PostgreSQL tables (managed by Alembic + LangGraph checkpointer):

- `chats` — conversation metadata
- `chat_messages` — message history per chat
- `agent_runs` — execution records
- `agent_events` — LLM / tool events per run
- `agent_memory_facts` — cross-chat memory store
- `langgraph_checkpoint_*` — LangGraph checkpointer tables

Run migrations:
```bash
uv run alembic upgrade head
```

---

## Agent Memory and Skills

### Memory tools
`memory_get_current_task`, `memory_search_chats`, `memory_get_chat_messages`,
`memory_list_recent_runs`, `memory_get_run_events` — see `docs/MEMORIA.md`.

### Skills
Local Markdown guides under `skills/`. The agent discovers them and injects a `<skills>` catalog
into the system prompt. Guides are read on demand via `skill_get_guide`. See `docs/skills-implementation.md`.

### Date/time
`get_current_date` (`src/agent/internal_tools/datetime_tools.py`) returns the real current
date/time from the container's system clock, converted to `AGENT_TIMEZONE` (default
`America/Bogota`). Weekday/month names are Spanish, computed from fixed tables (no OS locale
dependency). The agent must call it instead of guessing "today" from the conversation or from
training data — see `system.promt.md` § "Fecha y hora".

---

## Turn Lifecycle

```
User message
  → AgentRunner.run_agent_turn()
    → DB: persist user message, create AgentRun
    → graph.ainvoke(input, config={thread_id: chat_id})
      → LangGraph: load checkpoint (history)
      → LLM: generate response or tool call
      → If tool call: execute tool (BMC / memory / skill / A2A)
      → Repeat until final response
    → DB: persist assistant message, close AgentRun
  → Return ChatResponse
```
