# Implementación de skills (local)

AgentForge integra **guías Markdown locales** bajo la carpeta `skills/` del repositorio. El mecanismo depende de la **rama de producto** (dos líneas en paralelo).

## Dos ramas

| Aspecto | Rama `agent-base` (LangChain estándar) | Rama `deep-agent-base` (`deepagents`) |
|--------|----------------------------------------|----------------------------------------|
| Grafo | `create_agent` en [`src/agent/agent.py`](../src/agent/agent.py) | `create_deep_agent` + `FilesystemBackend` |
| Descubrimiento | Bloque XML `<skills>` al final del **system prompt** | Índice **Skills System** de Deep Agents |
| Detalle de una guía | Tool interna `skill_get_guide` | Lectura progresiva vía herramientas de fichero del arnés |
| Formatos en disco | `skills/<stem>.md` y/o `skills/<dir>/SKILL.md` | `skills/<dir>/SKILL.md` (Agent Skills) |

Política operativa del modelo (cuándo usar skills, límites): [`base.prompt.md`](../base.prompt.md).

---

## Rama `agent-base`

Esta es la línea **sin** dependencia de `deepagents`: catálogo en el prompt y tool `skill_get_guide`.

### Formato en disco

Se admiten **dos layouts** (mismo stem no puede duplicarse; si existen ambos, gana el archivo plano):

```text
skills/
  crear_correo.md              # stem = crear_correo
  revisar_caso_bmc/
    SKILL.md                     # stem = revisar_caso_bmc
  example/
    SKILL.md                     # ejemplo versionado en git
```

- **Descripción breve** para el catálogo: campo `description:` del frontmatter YAML, o el primer título `#` del cuerpo, o fallback `Guía <stem>`.
- Validación del stem: letras, números, guión y guión bajo; sin rutas ni `..`.

### Catálogo en el system prompt

Al cargar el prompt ([`src/agent/prompts.py`](../src/agent/prompts.py) → `finalize_system_prompt`), si hay al menos una guía se añade al **final** del system prompt un bloque como:

```xml
<skills>
crear_correo => guia para crear un correo
example => Skill de ejemplo versionada en el repositorio...
</skills>
```

Si **no** hay skills en disco, **no** se inyecta nada (ni etiquetas vacías). El mensaje del usuario en cada turno va **sin prefijos** (ver [`src/agent/runtime/runner.py`](../src/commons/runner.py)).

Implementación: [`src/config/skill_catalog.py`](../src/config/skill_catalog.py) (`discover_skill_entries`, `build_skills_catalog_xml`, `read_skill_guide_json`).

### Tool `skill_get_guide`

Registrada en [`src/agent/internal_tools/skill_tools.py`](../src/agent/internal_tools/skill_tools.py). Lee `skills/<stem>.md` o `skills/<stem>/SKILL.md` con límites de tamaño y validación de ruta. El modelo debe usar stems listados en `<skills>`.

### Recarga

Tras **añadir, renombrar o cambiar** archivos bajo `skills/` (o su frontmatter/descripción usada en el catálogo), hay que **reconstruir el agente** (`build_agent` / `POST /stop` + `POST /start` en HTTP) para que el bloque `<skills>` se regenere. Los cambios solo en el cuerpo de una guía ya existente se ven en la siguiente llamada a `skill_get_guide` sin reinicio del catálogo.

### Tests

[`test/test_skill_catalog.py`](../test/test_skill_catalog.py) — descubrimiento, XML, lectura dual y conflictos de stem (`tmp_path`, sin BD).

---

## Rama `deep-agent-base`

Esta sección describe la integración mediante el paquete **[`deepagents`](https://pypi.org/project/deepagents/)** de LangChain: *agent harness* con planificación, sistema de ficheros virtual, middleware de skills y más.

### Documentación oficial (Deep Agents)

| Recurso | Enlace |
|--------|--------|
| Deep Agents (visión general, Python) | [docs.langchain.com — Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview) |
| Skills en Deep Agents | [docs.langchain.com — Skills](https://docs.langchain.com/oss/python/deepagents/skills) |
| Backends de filesystem | [docs.langchain.com — Backends](https://docs.langchain.com/oss/python/deepagents/backends) |
| Especificación Agent Skills | [agentskills.io — Specification](https://agentskills.io/specification) |
| Código fuente | [github.com/langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) |

### Qué cambió respecto a la línea LangChain anterior

El snapshot previo al arnés Deep Agents está etiquetado en git como **`base-agent`** (histórico: `create_agent` con catálogo por turno en el mensaje del usuario). En **`deep-agent-base`** el grafo usa **`create_deep_agent`**, un **`FilesystemBackend`** anclado a la raíz del repositorio (`virtual_mode=True`) y la lista de fuentes **`skills=["/skills/"]`**.

En esta rama **no** se antepone texto de catálogo al mensaje del usuario ni existe la tool **`skill_get_guide`**. El modelo descubre skills mediante el bloque **Skills System** que inyecta Deep Agents y las herramientas de fichero del propio arnés.

### Formato en disco (solo local, sin remotas)

Cada skill es un directorio bajo **`skills/`** con un archivo obligatorio **`SKILL.md`**:

```text
skills/
  example/
    SKILL.md          # obligatorio: frontmatter YAML + instrucciones Markdown
  mi-procedimiento/
    SKILL.md
    datos.csv         # opcional: adjuntos referenciados desde SKILL.md
```

#### Ejemplo mínimo de `SKILL.md`

```markdown
---
name: example
description: Cuándo usar esta skill en una frase clara (ayuda al modelo a hacer matching).
---

# Título de la skill

Pasos o reglas que el modelo debe seguir cuando aplique esta skill.
```

Restricciones relevantes del estándar (resumen): el campo **`name`** debe coincidir con el nombre del directorio padre; **`description`** tiene tope de caracteres según la spec — ver [Agent Skills specification](https://agentskills.io/specification).

En el repo hay una skill **versionada de ejemplo**: [`skills/example/SKILL.md`](../skills/example/SKILL.md). El resto de ficheros bajo `skills/` pueden seguir ignorados por git salvo que añadas reglas `!` en [`.gitignore`](../.gitignore) para rutas concretas.

#### Código de referencia (extracto)

```python
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

repo_root = Path(__file__).resolve().parents[2]
backend = FilesystemBackend(root_dir=repo_root, virtual_mode=True)

graph = create_deep_agent(
    llm,
    tools,
    system_prompt=...,
    checkpointer=checkpointer,
    store=store,
    backend=backend,
    skills=["/skills/"],
)
```

Las rutas en `skills=` son rutas **virtuales POSIX** vistas por el backend (p. ej. `/skills/` → carpeta `skills/` dentro de `repo_root` cuando `virtual_mode=True`).

### Recarga en runtime y reinicios (Deep Agents)

#### Skills

Según la documentación de Deep Agents, al **crear el agente** se indexa el **frontmatter** de cada `SKILL.md` para el descubrimiento inicial; el cuerpo detallado sigue el patrón de **divulgación progresiva** cuando una skill encaja ([Skills](https://docs.langchain.com/oss/python/deepagents/skills)).

En la práctica:

- **Nueva skill, carpeta nueva o cambio en `name` / `description` en frontmatter**: suele hacer falta **volver a construir el grafo** (reentrada a `build_agent` / reinicio del proceso del servidor HTTP).
- **Cambios solo en el cuerpo Markdown** de un `SKILL.md` ya existente: en despliegues con backend de ficheros, la siguiente lectura del archivo puede ya reflejar el contenido nuevo; **confirma el comportamiento** en tu versión de `deepagents`.

#### Seguridad del `FilesystemBackend`

El backend de sistema de ficheros otorga al agente lectura/escritura sobre rutas resolubles bajo la raíz configurada. Para **APIs HTTP** expuestas a red, LangChain recomienda valorar backends alternativos (`StateBackend`, `StoreBackend`, sandboxes); aquí se usa ficheros locales por requisito del proyecto — limita permisos del proceso y revisa la [documentación de Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) (sandboxes / permisos).

---

## Común a ambas ramas

### MCP (sin recarga dinámica de URLs)

Las sesiones MCP se abren en el contexto de [`build_agent`](../src/agent/agent.py): **no** hay recarga dinámica de URLs MCP sin recomponer el agente.

Para actualizar la lista de servidores MCP **sin** perder el hilo de conversación cuando reinicies el proceso:

1. Persiste siempre el mismo **`thread_id`** (en AgentForge: `thread_id=str(chat_id)` del checkpointer Postgres).
2. Tras reinicio o `stop`/`start`, el historial del hilo se **rehidrata** desde el checkpointer al seguir usando el mismo chat.

Operación MCP (recarga, límites): [`docs/MCP.md`](MCP.md).

### System prompt (archivo, inline o Langfuse)

La cadena de carga del **system prompt** está en [`src/agent/prompts.py`](../src/agent/prompts.py): precedencia `SYSTEM_PROMPT` → Langfuse (`LANGFUSE_PROMPT_NAME` + `LANGFUSE_PROMPT_LABEL`) → archivo local; siempre puede añadirse `base.prompt.md`. En **`agent-base`**, además, el bloque `<skills>` si hay guías. Igual que MCP y el grafo, un cambio de prompt remoto o de archivo **solo aplica** tras **reconstruir el agente** (`build_agent` / `POST /stop` + `POST /start` en HTTP). Resumen de variables: [`README.md`](../README.md).

## Referencias cruzadas

- Memoria (checkpointer, BD, `memory_*`, store): [`MEMORIA.md`](MEMORIA.md)
- Arquitectura general: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Política operativa del modelo: [`base.prompt.md`](../base.prompt.md)
