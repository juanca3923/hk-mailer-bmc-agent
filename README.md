# Agente BMC ARUS

Agente de inteligencia artificial para gestión de **incidentes** y **órdenes de trabajo** en
**BMC Helix ARUS**. Basado en `agent_forge` (LangGraph + LangChain) con 12 herramientas internas
que interactúan directamente con la API REST de BMC Helix AR.

---

## Qué puede hacer

| Dominio | Herramientas |
|---------|-------------|
| **Sesión** | `bmc_health_check` — verifica la sesión JWT |
| **Órdenes de trabajo** | `bmc_create_work_order`, `bmc_get_work_order`, `bmc_add_work_order_note`, `bmc_add_work_order_attachment`, `bmc_update_work_order_status`, `bmc_close_work_order` |
| **Incidentes** | `bmc_create_incident`, `bmc_get_incident`, `bmc_add_incident_note`, `bmc_add_incident_attachment`, `bmc_close_incident` |
| **Archivos del correo** | `bmc_attach_staged_files` — adjunta a un Incidente/WO los archivos que otro agente dejó en la carpeta compartida (ver [Adjuntos](#adjuntos-y-carpeta-compartida)) |

Además hereda las capacidades de `agent_forge`:
- Memoria de conversaciones (checkpointer PostgreSQL).
- Skills locales en `skills/` (guías Markdown).
- API HTTP (FastAPI) y CLI interactiva.
- Soporte de LLM: Ollama, OpenAI o Anthropic.
- Observabilidad opcional con Langfuse.
- Comunicación A2A con otros agentes (opcional).

---

## Requisitos

- Python **≥ 3.14**
- [`uv`](https://docs.astral.sh/uv/) instalado
- PostgreSQL corriendo (para memoria y trazas)
- Credenciales de servicio de **BMC Helix ARUS** (`BMC_BASE_URL`, `BMC_USERNAME`, `BMC_PASSWORD`)
- Un proveedor LLM: Ollama (local), OpenAI o Anthropic

---

## Instalación y preparación

```bash
# 1. Instalar dependencias
uv sync

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env: completar BMC_PASSWORD, LLM_PROVIDER, DATABASE_URL, etc.

# 3. Inicializar la base de datos
uv run alembic upgrade head
```

---

## Ejecución

### CLI (modo interactivo)

```bash
uv run agente
```

Al iniciar, el agente hace login en BMC automáticamente. Si `BMC_BASE_URL` no está configurada,
arranca sin herramientas BMC (útil en desarrollo).

### Servicio HTTP (FastAPI)

```bash
# Desarrollo con autoreload
uv run uvicorn http_api.app:app --reload --port 8000

# Producción
uv run agent-bmc-http
```

### Docker

```bash
# Producción
docker build -t agent-bmc:latest .
docker run --rm -p 8000:8000 \
  -e BMC_BASE_URL=https://arus-dev-restapi.onbmc.com \
  -e BMC_USERNAME=webservice_mosaico@arus.com.co \
  -e BMC_PASSWORD=<clave> \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host:5432/agent_bmc \
  -e LLM_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=<clave> \
  agent-bmc:latest
```

---

## Configuración mínima (`.env`)

```bash
# BMC (obligatorio)
BMC_BASE_URL=https://arus-dev-restapi.onbmc.com
BMC_USERNAME=webservice_mosaico@arus.com.co
BMC_PASSWORD=<clave-api>
BMC_ALLOW_WRITE=true
# Única carpeta desde la que se pueden adjuntar archivos (sin definir: adjuntos deshabilitados)
BMC_ATTACHMENT_BASE_DIR=/app/data/ticket_files

# LLM
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=<clave>

# Base de datos
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_bmc

# Identificador del agente
AGENT_SLUG=agent_bmc
```

---

## Adjuntos y carpeta compartida

Los archivos nunca viajan por el protocolo A2A ni por el contexto del LLM. Otro agente (p. ej. `hk-mailer-agent`) deja en una **carpeta compartida** `<BMC_ATTACHMENT_BASE_DIR>/<staging_id>/` los archivos y un `manifest.json`:

```json
{"files": [{"name": "correo_original.eml", "description": "Correo original recibido"},
           {"name": "captura.png", "description": "Captura del error"}]}
```

El agente solo recibe el `staging_id` y llama a `bmc_attach_staged_files(ticket_type, ticket_number, staging_id)`. Cada archivo se sube como su propia entrada del log de actividad (la `description` es el texto de la nota). Los archivos que superan `BMC_MAX_ATTACHMENT_BYTES` (10 MiB por defecto) o que falten no se suben y se listan en **una nota** del ticket.

**Seguridad:** `BMC_ATTACHMENT_BASE_DIR` es la **única** carpeta de la que se puede adjuntar. La ruta se resuelve por completo (`..` y enlaces simbólicos incluidos) y todo lo que quede fuera se rechaza, también en `bmc_add_*_attachment`. Sin definir, los adjuntos quedan deshabilitados. En el contenedor del BMC conviene montar la carpeta **solo lectura**; en Kubernetes, un volumen `ReadWriteMany` compartido con el agente que escribe.

---

## Endpoints HTTP principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/chat` | Chat bloqueante |
| `POST` | `/chat/stream` | Chat en streaming (SSE) |
| `GET` | `/status` | Estado del agente |
| `GET` | `/chats` | Historial de chats |
| `GET` | `/runs/last` | Último run detallado |
| `POST` | `/start` / `/stop` | Control del agente |

---

## Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [`CLAUDE.md`](CLAUDE.md) | Guía completa para Claude Code (estructura, tools, extensión) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Arquitectura del agente y capa BMC |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Historial de cambios |
| [`docs/MEMORIA.md`](docs/MEMORIA.md) | Checkpointer, historial y memory tools |
| [`docs/A2A.md`](docs/A2A.md) | Protocolo Agent-to-Agent |
| [`docs/MCP.md`](docs/MCP.md) | Herramientas MCP adicionales (opcionales) |
| [`docs/ALEMBIC.md`](docs/ALEMBIC.md) | Migraciones de base de datos |
| [`test/README.md`](test/README.md) | Inventario de tests |

---

## Variables de entorno completas

Ver [`.env.example`](.env.example) para la lista completa con descripciones.
