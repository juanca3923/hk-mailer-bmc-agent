# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

**agent-bmc** is a LangGraph-based AI agent for managing **incidents** and **work orders** in
**BMC Helix ARUS**. It is built on top of `agent_forge` — a production-ready Python framework for
conversational agents — and extends it with 12 internal LangChain tools that wrap the BMC Helix
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
│   │       ├── bmc_tools.py          # 12 BMC LangChain @tool functions + get_bmc_tools()
│   │       ├── memory_tools.py       # memory_* tools (chat/run history)
│   │       ├── skill_tools.py        # skill_get_guide
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
│   │   │       ├── multipart_builder.py
│   │   │       ├── work_order_operations.py
│   │   │       └── incident_operations.py
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
        │   ├─ BMC tools        (12 tools → BmcClient → BMC Helix REST)
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

### Business defaults — BMC tickets

Fixed values injected by `src/bmc/libs/business_defaults.py` into every `bmc_create_work_order`
and `bmc_create_incident` call. The LLM never sees these as tool parameters.

| Variable | Fallback | Used in |
|----------|----------|---------|
| `BMC_DEFAULT_COMPANY` | `ARUS` | WO + incident `Company` |
| `BMC_DEFAULT_FIRST_NAME` | `Mosaico` | WO + incident `First_Name` |
| `BMC_DEFAULT_LAST_NAME` | `WebServices` | WO + incident `Last_Name` |
| `BMC_DEFAULT_CUSTOMER_FIRST_NAME` | `Mosaico` | WO `Customer First Name` |
| `BMC_DEFAULT_CUSTOMER_LAST_NAME` | `WebServices` | WO `Customer Last Name` |
| `BMC_DEFAULT_CUSTOMER_COMPANY` | `ARUS` | WO `Customer Company` |
| `BMC_DEFAULT_ASSIGNED_GROUP` | `MESA MARCO` | Default of the `assigned_group` **tool parameter** of `bmc_create_incident` (not a fixed injection — the LLM should override it with the value from the `categorias-incidentes` skill row) |
| `BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP` | `MESA MARCO` | Default of the `assigned_group` **tool parameter** of `bmc_create_work_order` (not a fixed injection — the LLM should override it with the value from the `categorias-requerimientos` skill row) |

### Required — LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `openai` \| `anthropic` \| `huggingface` |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Model name when using Ollama |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `HUGGINGFACE_API_KEY` | — | Required when `LLM_PROVIDER=huggingface` |
| `HUGGINGFACE_MODEL` | — | Required when `LLM_PROVIDER=huggingface`; repo id routed through HF Inference Providers (e.g. `meta-llama/Llama-3.3-70B-Instruct`). Must support tool calling — not guaranteed for every model |
| `HUGGINGFACE_PROVIDER` | `auto` | Optional underlying inference provider behind the HF router (e.g. `together`, `novita`, `cerebras`) |
| `HUGGINGFACE_BILL_TO` | — | Optional HF organization to bill inference to (`InferenceClient(bill_to=...)`); empty bills the token's own account |
| `HUGGINGFACE_ALLOW_LEGACY_TLS` | `false` | **Dev-only.** Relaxes OpenSSL's security level (`SECLEVEL=1`) for `huggingface_hub`'s HTTP client, to accept a corporate TLS-inspection root CA with a weak key (<2048-bit RSA) or SHA-1 signature. Certificate verification stays on; requires `SSL_CERT_FILE` pointing to a bundle that trusts that CA. Never enable in production — fix is reissuing the CA with a modern key |

### Required — Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/agent_bmc` | Postgres DSN |

### Agent identity

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_SLUG` | `agent_bmc` | Unique identifier (pattern `^[a-z][a-z0-9_]*$`) |

### System prompt precedence

1. `SYSTEM_PROMPT` (inline env var) — highest priority
2. `LANGFUSE_PROMPT_NAME` (if all Langfuse vars are set)
3. `SYSTEM_PROMPT_PATH` (file path)
4. `system.promt.md` in the repo root — default (BMC-specific)

---

## BMC Internal Tools

All 12 tools live in `src/agent/internal_tools/bmc_tools.py` and share a lazy-initialized
`BaseToolHandler` from `src/bmc/libs/tool_handler.py`.

| Tool | Operation | AR Form |
|------|-----------|---------|
| `bmc_health_check` | Verify JWT session | GET ping |
| `bmc_create_work_order` | Create WO | `WOI:WorkOrderInterface_Create` |
| `bmc_get_work_order` | Search WO by ID | `WOI:WorkOrderInterface` |
| `bmc_add_work_order_note` | Add note without attachment (rejects if `Closed`) | `WOI:WorkInfo` |
| `bmc_add_work_order_attachment` | Add note with file attachment (rejects if `Closed`) | `WOI:WorkInfo` multipart |
| `bmc_update_work_order_status` | PUT intermediate status (rejects if `Closed`) | `WOI:WorkOrderInterface` |
| `bmc_close_work_order` | Ownership PUT (`ASCHG`) → Completed PUT+note → Closed PUT+note (rejects if `Closed` or not opened by `BMC_USERNAME`) | `WOI:WorkOrderInterface` + `WOI:WorkInfo` |
| `bmc_create_incident` | Create incident (Impact/Urgency fixed; `assigned_group` is a tool parameter) | `HPD:IncidentInterface_Create` |
| `bmc_get_incident` | Search incident by number | `HPD:IncidentInterface` |
| `bmc_add_incident_note` | Add note without attachment (rejects if `Closed`) | `HPD:WorkLog` |
| `bmc_add_incident_attachment` | Add note with file attachment (rejects if `Closed`) | `HPD:WorkLog` multipart |
| `bmc_close_incident` | Ownership PUT (`Assignee`) → Resolved PUT with `Status_Reason=Closing` (rejects if `Closed` or not opened by `BMC_USERNAME`) | `HPD:IncidentInterface` |

All tools return a JSON string with `{"success": bool, "message": "..."}`. On success, `message`
contains TOON-encoded structured data. On error, `message` contains a user-facing Spanish error.

Business-rule guards (`src/bmc/libs/helpers/ticket_guards.py`) run before any write: `require_not_closed`
rejects writes on tickets already `Closed`; `require_submitter` (close only) rejects closing a ticket
whose `Submitter` does not match `BMC_USERNAME` — adding notes/attachments to such a ticket is still
allowed.

---

## Adding New BMC Tools

1. Add input/output models to `src/bmc/type_defs/inputs.py` and `outputs.py` if needed.
2. Add AR field constants to `src/bmc/libs/constants.py` if needed.
3. Add the HTTP method to `src/bmc/libs/api_client.py`.
4. Add a helper in `src/bmc/libs/helpers/` if the operation has multiple steps.
5. Add the `@tool` function to `src/agent/internal_tools/bmc_tools.py` following the lazy
   handler pattern (`h = _get_handler()`).
6. Register it in `_ALL_BMC_TOOLS` list at the bottom of that file.
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
