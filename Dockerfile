# Producción: solo lo necesario para ejecutar el servicio HTTP (sin docs ni README).
# Ver README sección "Docker" para uso.

FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 appuser

# Instalar uv y dependencias del proyecto (sin grupo dev).
# Incluir uv.lock: sin él, uv re-resuelve desde PyPI y el árbol puede diferir del repo.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY system.promt.md system.promt.default.md base.prompt.md ./
# Guías locales (catálogo <skills>); sin skills/example/ (solo plantilla en repo).
COPY skills ./skills
RUN rm -rf ./skills/example \
    && pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev \
    && pip uninstall -y uv \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app/logs

ENV PATH="/app/.venv/bin:$PATH"
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn http_api.app:app --host ${HTTP_HOST:-0.0.0.0} --port ${HTTP_PORT:-8000}"]
