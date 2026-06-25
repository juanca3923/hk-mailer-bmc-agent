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

- Python objetivo: **3.11**.
- No capturar excepciones demasiado amplias (`Exception`, `BaseException`).
- Logging: formato estilo `%` con el módulo `logging`.
- `requests`: métodos con `timeout=...` explícito siempre.
- Comentarios de nota permitidos: `FIXME`, `XXX`, `TODO`.
- Evitar duplicación por copiar/pegar; refactorizar bloques repetidos.

## Seguridad

- No registrar datos sensibles (contraseñas, tokens, secretos).
- No hardcodear credenciales ni valores propios de un entorno.
- No leer, modificar ni commitear `.env` ni variantes.
- Validar entradas externas; evitar `except` silenciosos.

## Disciplina de cambio

- Cambios mínimos y acotados; reutilizar utilidades y patrones del repo.
- No introducir cambios incompatibles sin indicarlo claramente.
- Mensajes de commit: seguir `.claude/rules/commits-espanol.md`.
