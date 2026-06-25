# Mensajes de commit

Todo el contenido del commit (asunto y cuerpo) se redacta en **español**.

## Tipo de cambio (obligatorio en el cuerpo)

| Etiqueta | Cuándo usarla |
|---|---|
| `BUG` | Corrección de un fallo de comportamiento, regresión o error reportado. |
| `FEATURE` | Funcionalidad nueva visible (API, flujo, endpoint nuevo). |
| `RELATED` | Cambio motivado por otro refactor/feature/tarea previa; adaptación técnica sin ser bug puntual ni feature nueva protagonista. |

Si varias etiquetas aplican, elige la que represente el **resultado principal** y menciona lo demás en `## Contexto`.

## Plantilla (Markdown compacto)

```markdown
Corrige ids de recurso del calendario de liquidación

## Tipo
BUG

## Archivos
- `src/commons/runner.py`: descripción breve del cambio.
- `src/config/settings.py`: descripción breve del cambio.
```

## Reglas

- **Asunto**: una línea, imperativo, en español. Sin punto final.
- **Cuerpo**: máx. ~12 líneas incluyendo listas.
- Rutas entre acento grave `` ` `` para destacarlas.
- Solo listar archivos **realmente modificados** en el commit.
- Orden de archivos: alfabético o por capa.

## Secciones opcionales (solo si aportan)

| Sección | Uso | Extensión |
|---|---|---|
| `## Contexto` | Una frase: por qué, impacto no obvio. | 1 línea |
| `## Refs` | Enlace a issue/ticket/`#42`. | 1 línea |
| `## Riesgo` | `bajo` / `medio` / `alto` si toca datos, auth o despliegue. | 1 palabra |

## Prefijo convencional en asunto (opcional, solo si CI lo requiere)

`fix:` | `feat:` | `chore:` | `refactor:` — no sustituye al `## Tipo` en el cuerpo.
