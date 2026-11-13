# Estándar Python (equipo)

Aplica lo siguiente al trabajar en archivos Python de este repositorio.

## Documentación automática

Cuando el cambio afecte comportamiento visible, contratos de API, variables de entorno, estructura del repo o trazabilidad de producto, **lee y aplica `.claude/commands/docs-maintainer.md` en el mismo flujo que el código**. No es opcional ni diferible.

## Idioma

- Docstrings y comentarios en código: **inglés**.
- Documentación Markdown del repo (`README.md`, `docs/`): **español**.

## Docstrings

- Delimitador: comillas triples dobles `"""` exclusivamente para docstrings. En el resto del código usar comilla simple `'...'` (incluidas f-strings).
- Estilo **NumPy** ([numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html)): módulos, clases públicas y funciones/métodos públicos siguen las secciones `Parameters`, `Returns`, `Raises`, `Attributes`.
- Cada archivo: docstring de módulo como primer elemento del fichero.
- Sin docstring en `__init__`.
- Docstrings al inicio del ámbito; nunca a mitad de función.

### Ejemplo (estilo NumPy)

```python
"""Module-level summary in one line."""


class Greeter:
    """Builds greeting messages for a named subject.

    Attributes
    ----------
    name : str
        Display name used in greetings.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def hello(self, punctuation: str = '.') -> str:
        """Return a one-line greeting.

        Parameters
        ----------
        punctuation : str, optional
            Character(s) appended after the name, by default ``"."``.

        Returns
        -------
        str
            Greeting string including ``name`` and ``punctuation``.
        """
        return f'Hello, {self.name}{punctuation}'
```

## Tipado y estilo

- PEP 8. Longitud de línea: máx. **120 caracteres**. Tamaño de módulo: máx. **1000 líneas**.
- Tipado estricto en parámetros y retorno; genéricos siempre parametrizados (`dict[str, int]`, no `dict`). `Any` solo cuando no haya tipo concreto razonable — anotar con `# noqa: ANN401` y comentario breve.
- Imports: sin importaciones relativas; rutas completas desde la raíz de paquetes. Orden: (1) stdlib, (2) terceros, (3) local.

```python
# Mal
def get_user(data: dict) -> list:
    ...

# Bien
def get_user(data: dict[str, str]) -> list[User]:
    ...
```

## Convenciones de nombres

- Funciones/métodos y variables/argumentos: `snake_case`
- Clases: `PascalCase`
- Constantes: `UPPER_CASE`
- Módulos/paquetes: `snake_case`

## Docstring de humanos vs. descripción de tool para el LLM

En una función `@tool` (o expuesta al LLM por otro medio, ej. `StructuredTool.from_function`),
el **docstring NumPy** y la **descripción que ve el LLM** son dos textos con audiencias
distintas — se parecen, pero no son lo mismo, y confundirlos genera ruido en ambos lados:

- **Docstring (NumPy, para quien lee el código)**: sigue el estándar de la sección
  "Docstrings" de arriba. La sección `Parameters` puede **omitirse o resumirse en una línea**
  cuando cada parámetro ya está documentado en su propio `Field(description=...)` dentro de
  `Annotated[...]` — ese `Field` es la fuente de verdad del parámetro, no lo dupliques a mano
  en dos lugares. No uses un placeholder vago tipo *"ver la tool"*; si se omite, dilo
  explícitamente y en una sola línea (ej. `Parameters: cada uno documentado en su propio
  Annotated/Field — ver el schema de la tool.`).
- **Descripción del LLM**: se pasa **explícitamente** con `@tool(description=...)` (o el
  parámetro `description=` de `StructuredTool.from_function`) — **nunca** se deja que
  LangChain la infiera del docstring completo. Debe ser concisa, en inglés, y centrada en
  **cuándo y por qué usar la tool** (comportamiento, efectos secundarios, restricciones) — no
  repitas el shape de retorno (`JSON con success/message`) si es igual en todas las tools, ni
  uses marcado RST (dobles backticks, subrayados `----------`) pensado para Sphinx.

## Orden de miembros en una clase

Ni PEP 8 ni la guía de estilo de Google prescriben un orden — queda a criterio del equipo.
Convención de este repo (público primero, "step-down": el lector ve la interfaz antes que el
detalle de implementación):

1. Docstring de la clase y constantes de clase (`UPPER_CASE`).
2. `__init__` y otros dunders (`__repr__`, `__eq__`, etc.).
3. `@property` (getters/setters).
4. Métodos públicos, en el orden en que naturalmente se llamarían.
5. Métodos privados (`_prefijo`) y `@staticmethod`/`@classmethod` de apoyo — cada uno
   ubicado junto al método público que lo usa (antes o después, lo que se lea mejor), no
   agrupados aparte al final. Si un helper lo usan varios métodos públicos, va junto al
   primero que lo necesita.

## Límites de diseño (verificados con Pylint + `.pylintrc`)

| Métrica | Máximo |
|---|---|
| `return` por función | 3 |
| Parámetros por función/método | 5 |
| Variables locales por función/método | 15 |
| Ramas por función/método | 12 |
| Sentencias por función/método | 50 |
| Niveles de anidación | 5 |
| Atributos por clase | 7 |
| Expresiones booleanas en un `if` | 5 |

## Pylint y herramientas

- Python objetivo: **3.14**.
- **Mypy** (`uv run mypy`, config en `mypy.ini`) debe quedar en 0 errores. Preferir anotar o acotar tipos antes que `# type: ignore`; si es inevitable, usar el código de error concreto (`# type: ignore[attr-defined]`). `warn_unused_ignores` está activo.
- No capturar excepciones demasiado amplias (`Exception`, `BaseException`).
- Logging: formato estilo `%` con el módulo `logging`.
- `requests`: métodos con `timeout=...` explícito siempre.
- Comentarios de nota permitidos: `FIXME`, `XXX`, `TODO`.
- Evitar duplicación por copiar/pegar; refactorizar bloques repetidos.

### Excepciones anchas justificadas

Un `except Exception` (con `# pylint: disable-next=broad-exception-caught` +
`# noqa: BLE001`) solo es aceptable cuando se cumplen **ambas** condiciones — nunca como
atajo para no pensar en los tipos reales:

1. Es el límite con código que **no tiene un tipo de excepción cerrado y estable que
   capturar** — un SDK/librería externa cuya propia documentación admite que propaga
   excepciones arbitrarias (ej. `Langfuse.get_prompt()`: *"Raises: Exception: Propagates
   any exceptions..."*), o un punto final de la aplicación después de agotar los tipos
   específicos conocidos (ver `agent/runtime/runner.py`: primero `asyncio.CancelledError`,
   luego `AgentError`, y solo al final el catch-all).
2. La **recuperación es idéntica sin importar el tipo de fallo** (loguear + degradar
   con gracia — devolver un fallback, cadena vacía, etc.) — no hay rama de manejo
   distinta por tipo de excepción que se esté evitando escribir.

Si aplica, el comentario junto al `except` debe explicar el **motivo** (por qué no hay un
tipo más específico y cuál es la recuperación), no solo repetir qué hace el código.
Ejemplos ya en el repo: `agent/prompts.py` (`fetch_prompt_from_langfuse`) y
`agent/runtime/runner.py` (los dos catch-all de `run_agent_turn`).

## Estructura del repositorio

- **Capas** (un paquete solo importa de los anteriores; nada importa hacia arriba): `type_defs`/`constants`/`exception` < `commons` < `config` < `database` < `services` < `agent` < `http_api`. `commons` es **puro**: no importa `config`, base de datos ni agente.
- **Un archivo, una responsabilidad:** los **tipos** (dataclass, `TypedDict`, `NamedTuple`, `Protocol`, `Enum`, alias `Literal`, modelos Pydantic) solo en `type_defs/`; las **constantes públicas** solo en `constants/<dominio>/` (las privadas `_X` y los objetos con comportamiento, como un `ContextVar` o una sesión, se quedan donde se usan); las clases y servicios, solos en su módulo.
- **Conjuntos cerrados** (estados, motivos): `StrEnum` en `type_defs/enums/`, una sola fuente de verdad.
- **Dónde va algo nuevo:** tipo → `type_defs/models/<dominio>/`; contrato entre capas → `type_defs/ports/`; valor fijo → `constants/<dominio>/`; lógica sin dependencias → `commons/<dominio>/`; acceso a base de datos → `services/persistence/`; cliente u operación de BMC → `services/bmc/`; tool del LLM → `agent/internal_tools/`.
- **Nada suelto:** no dejes archivos en la raíz de `commons/` ni de `services/`; usa un subpaquete por dominio. Mapa completo en `docs/ARCHITECTURE.md`.

## Seguridad

- No registrar datos sensibles (contraseñas, tokens, secretos).
- No hardcodear credenciales ni valores propios de un entorno.
- No leer, modificar ni commitear `.env` ni variantes.
- Validar entradas externas; evitar `except` silenciosos.

## Disciplina de cambio

- Cambios mínimos y acotados; reutilizar utilidades y patrones del repo.
- No introducir cambios incompatibles sin indicarlo claramente.
- Mensajes de commit: seguir `.claude/rules/commits-espanol.md`.
