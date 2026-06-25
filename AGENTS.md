# Política para agentes (plantilla reutilizable)

Documento **versionado en el repo** con reglas generales para humanos y asistentes de código. Cada proyecto puede añadir detalles en su **README** o en un **`.cursorrules`** acotado; este archivo define la **política común**.

## Alcance de los cambios

- Modificar **solo lo necesario** para la tarea solicitada en código.
- Evitar refactors amplios y archivos no relacionados con el objetivo.
- La **documentación obligatoria** del repo se actualiza **cuando corresponda** según las secciones siguientes; no cuenta como “documentación extra opcional”.

## Documentación obligatoria (existencia)

Los siguientes elementos **deben existir** en todo repositorio que siga esta plantilla:

1. **`README.md` en la raíz del proyecto** (obligatorio): punto de entrada al repo (qué es el proyecto, requisitos, cómo ejecutarlo, variables, enlaces a `docs/`, etc.).
2. **Carpeta `docs/`** (obligatoria), con **contenido mínimo**:
   - **`docs/ARCHITECTURE.md`** (o nombre equivalente acordado en el proyecto): **obligatorio** — estructura del código, componentes y flujos.
   - **`docs/CHANGELOG.md`** (o equivalente): **obligatorio** — historial de cambios con trazabilidad.
   - **Colección Postman** en **`.json`** bajo `docs/`: **obligatoria** — debe reflejar la API HTTP expuesta (en este repo: `docs/postman_agente_linux_server.json`).
   - **Cualquier documentación adicional** que el proyecto requiera (guías, procedimientos, datos de prueba, etc.) debe vivir también bajo **`docs/`**, respetando los formatos permitidos (ver más abajo).


## Mantenimiento: README, arquitectura, CHANGELOG y Postman

Mantener **alineados con el código** y **actualizarlos si el cambio lo amerita** (nuevas rutas, flujos, estructura, despliegue, etc.):

Si un cambio no afecta comportamiento, estructura ni operación, puede no requerir entrada en CHANGELOG; en la duda, una línea en el CHANGELOG es preferible a omitir.

## Carpeta `docs/` (formatos y documentación adicional)

- Toda documentación que no sea el `README.md` de la raíz debe vivir bajo **`docs/`** (incluidos los archivos mínimos ya listados arriba y **cualquier documentación adicional**: guías tipo Alembic, notas técnicas, fixtures, etc.).
- Archivos bajo `docs/` **solo** en **Markdown** (`.md`) o **JSON** (`.json`). El JSON se usa sobre todo para Postman, datos de prueba y artefactos estructurados similares.

## Convención de tipado

Para mantener el árbol libre de dispersión de tipos:

- **`src/type_defs/`**: todo el tipado del proyecto vive aquí (paquete importable como `type_defs`, no como `types`: el nombre `types` está reservado al módulo estándar de Python y provoca `ModuleNotFoundError` / colisiones).
  - **`type_defs/http/`**: modelos Pydantic (`BaseModel`) para contratos HTTP. Un archivo por dominio (`chat.py`, `status.py`, `runs.py`); `__init__.py` solo re-exporta. No deben vivir aquí `TypedDict`, `Protocol`, `dataclass` ni aliases.
  - **`type_defs/dicts/`**: `TypedDict`, `Protocol`, `dataclass` de capa compartida y aliases de tipo (e.g. `JsonDict`). Subdividir en archivos por dominio: `agent_turn.py`, `protocols.py`, `search_results.py`, `json_types.py`, `event_payloads.py`, `agent_memory.py`, etc.
  - `__init__.py` raíz re-exporta todo (`http/` + `dicts/`) para imports cómodos (`from type_defs import ...`).
- **No duplicar** definiciones de tipos en `services/`, `commons/`, `agent/` ni en el módulo que los usa; siempre importar desde `type_defs/`.
- **`Any` de librerías externas**: si una firma de interfaz externa (p. ej. LangChain `AsyncCallbackHandler`) impone `Any`, anotarlo en esa línea con `# noqa: ANN401` y un comentario breve explicando por qué es inevitable.

## Qué no duplicar aquí

- La descripción viva del dominio, el árbol detallado y los comandos concretos siguen en **README** y **ARCHITECTURE**; esta plantilla solo fija la política.

## Reglas mínimas en el editor

- Si el repo tiene [`.cursorrules`](.cursorrules), complementa o concentra reglas cortas para el IDE; esta plantilla es la referencia de política general.
