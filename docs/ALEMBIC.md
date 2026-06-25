# Alembic (migraciones Postgres)

Este proyecto usa **Alembic** para gestionar cambios de esquema en Postgres.

**Generar una migración** (después de cambiar `src/database/models.py`):

```bash
cd agent_linux_server
PYTHONPATH=src uv run alembic revision --autogenerate -m "descripción del cambio"
```

Se crea un archivo nuevo en `alembic/versions/`. Revísalo y luego **aplicar**:

```bash
PYTHONPATH=src uv run alembic upgrade head
```

### Si falla: "Can't locate revision identified by '...'"

Significa que **la base de datos** tiene en su tabla `alembic_version` una revisión (por ejemplo `8f3a2c1d4b5e`) de la que **no existe el archivo** en `alembic/versions/` (otro equipo, otro clone, o ese archivo nunca se guardó en el repo). Alembic no puede seguir sin ese archivo.

**Solución sin crear migraciones a mano:** decirle a la BD que su revisión actual es la que sí tienes en archivos (`6cbd2bf5599c`), para que autogenerate pueda generar la siguiente a partir de esa:

```bash
cd agent_linux_server
PYTHONPATH=src uv run alembic stamp 6cbd2bf5599c
```

Sustituye `6cbd2bf5599c` por la revisión que muestre `uv run alembic heads` (la única “head” que tienes en `versions/`). Con eso la tabla `alembic_version` queda en esa revisión y **no se ejecuta ningún SQL** en las tablas de la app; solo se actualiza el número de versión.

Después de hacer el `stamp`:

1. Genera la migración con el comando normal:
   ```bash
   PYTHONPATH=src uv run alembic revision --autogenerate -m "descripción"
   ```
2. Revisa el archivo generado en `alembic/versions/`.
3. Si la BD ya tenía columnas que la nueva migración intenta crear (porque antes se aplicó la revisión “perdida”), al hacer `upgrade head` puede salir *column already exists*. En ese caso:
   - o bien quitas esas columnas una vez en la BD y vuelves a ejecutar `upgrade head`,
   - o bien editas la migración generada para usar `ADD COLUMN IF NOT EXISTS` (por ejemplo con `op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS ...")`).

## Estructura

- `alembic/`
  - `env.py`: punto de entrada que Alembic ejecuta para:
    - configurar `target_metadata` (qué modelos ORM deben compararse al generar migraciones),
    - cargar la URL de la base de datos,
    - ejecutar en modo *offline*/*online*.
  - `versions/`: archivos de migración generados (secuenciados por `revision` y `down_revision`).
- `alembic.ini`: configuración base de Alembic (en este repo `env.py` sobrescribe la URL para usar `DATABASE_URL` del proyecto).

### `alembic/env.py`

En `env.py` se configura:
- `target_metadata`: metadatos desde `src/database/models.py` (clase `Base`) para que Alembic sepa qué tablas/columnas existen.
- `sqlalchemy.url`: Alembic usa una URL **sync** para migrar. Si tu `DATABASE_URL` viene con `+asyncpg`, `env.py` la transforma a `postgresql://...`.

> Importante: cuando cambies modelos ORM en `src/database/models.py`, Alembic necesita que `target_metadata` apunte correctamente a `Base.metadata`.

## Flujo recomendado para generar migraciones

1) Asegúrate de que Postgres esté accesible con `DATABASE_URL` (en `.env`).

2) Genera una migración automáticamente (autogenerate):

```bash
cd agent_linux_server
PYTHONPATH=src uv run alembic revision --autogenerate -m "describe el cambio"
```

3) Revisa el archivo generado en `alembic/versions/` (siempre).

4) Aplica la migración:

```bash
PYTHONPATH=src uv run alembic upgrade head
```

## Comandos útiles

- Ver historial / estado:
  - `PYTHONPATH=src uv run alembic current`
  - `PYTHONPATH=src uv run alembic history`
  - `PYTHONPATH=src uv run alembic heads`

- Migrar hacia atrás:
  - `PYTHONPATH=src uv run alembic downgrade -1` (una revisión)
  - `PYTHONPATH=src uv run alembic downgrade base` (todas)

## Notas sobre asyncpg y Alembic

- Tu app usa `SQLAlchemy async` (con `+asyncpg`) para runtime.
- Alembic ejecuta migraciones normalmente con un motor de conexión **sync**.
- Por eso el proyecto mantiene una URL sync para Alembic dentro de `alembic/env.py`.

## Checklist antes de commitear una migración

- El archivo nuevo aparece en `alembic/versions/`.
- `upgrade()` contiene las sentencias esperadas.
- Si aparece cualquier cambio “inesperado” por comparación autogenerate:
  - revisa el `target_metadata`,
  - revisa constraints/índices y tipos (por ejemplo `JSONB`, `UUID`, timezone).
