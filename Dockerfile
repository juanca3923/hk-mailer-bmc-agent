# Producción: solo lo necesario para ejecutar el servicio HTTP (sin docs ni README).
# Ver README sección "Docker" para uso.

FROM python:3.14-slim

WORKDIR /app

RUN useradd -m -u 1000 appuser

# Instalar uv y dependencias del proyecto (sin grupo dev).
# Incluir uv.lock: sin él, uv re-resuelve desde PyPI y el árbol puede diferir del repo.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY system.promt.md base.prompt.md ./
# Guías locales (catálogo <skills>); sin skills/example/ (solo plantilla en repo).
COPY skills ./skills
# Dos RUN a propósito: instalar uv, sincronizar el venv y desinstalar uv en una MISMA capa producía,
# con el image store containerd de Docker, una imagen vacía (capa con marcas de borrado de "/"):
# fallaba al arrancar con "unable to find user appuser".
# --link-mode copy: uv enlaza los paquetes por hardlink y containerd guarda esa capa vacía
# (el siguiente RUN no encuentra /bin/sh ni appuser).
RUN rm -rf ./skills/example \
    && pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --link-mode copy
RUN pip uninstall -y uv \
    && mkdir -p /app/logs /app/data/ticket_files \
    && chown -R appuser:appuser /app/logs /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000
# Zona horaria del contenedor (reloj de sistema) y de la tool `get_current_date`
# (AGENT_TIMEZONE en Settings usa el mismo valor por defecto).
ENV TZ=America/Bogota

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn http_api.app:app --host ${HTTP_HOST:-0.0.0.0} --port ${HTTP_PORT:-8000}"]
