"""Carga el system prompt desde archivos, Langfuse o variables de entorno."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langfuse import Langfuse

from config import get_logger
from config.skill_catalog import build_skills_catalog_xml
from constants.agent import BASE_PROMPT_FILENAME, LANGFUSE_FETCH_TIMEOUT_S
from exception import AgentConfigError

if TYPE_CHECKING:
    from config.settings import Settings

logger = get_logger()


def load_system_prompt_for_settings(settings: "Settings") -> str:
    """Resuelve el system prompt según prioridad: inline > Langfuse > archivo.

    Orden:
      1. ``SYSTEM_PROMPT`` (texto inline no vacío).
      2. Si ``LANGFUSE_PROMPT_NAME`` está definido (y credenciales Langfuse), intento
         remoto; si hay texto válido, se usa como principal.
      3. Archivo ``SYSTEM_PROMPT_PATH`` o ``system.promt.md`` en la raíz del repo.
      4. Si no hay texto usable en ninguna fuente, ``AgentConfigError`` con detalle.
    """
    inline = (settings.system_prompt_env or "").strip()
    if inline:
        logger.info("Usando prompt inline: %s", inline)
        return finalize_system_prompt(append_base_fragment(inline, settings.repo_root()))

    lf_name = (settings.langfuse_prompt_name or "").strip()
    if lf_name:
        fetched = fetch_prompt_from_langfuse(settings, lf_name)
        if fetched.strip():
            logger.info("Usando prompt desde Langfuse: %s", fetched.strip())
            return finalize_system_prompt(append_base_fragment(fetched.strip(), settings.repo_root()))

    path = settings.resolved_system_prompt_file()
    if path.exists():
        try:
            main_text = read_required(path)
            return finalize_system_prompt(append_base_fragment(main_text, path.parent))
        except AgentConfigError as err:
            detail_file = str(err)
            if lf_name:
                raise AgentConfigError(
                    "No se pudo obtener un system prompt válido: Langfuse no devolvió "
                    "texto usable o falló la petición, y el archivo local está vacío o no "
                    f"es válido. Detalle archivo: {detail_file}"
                ) from err
            raise

    if lf_name:
        raise AgentConfigError(
            "No se pudo obtener un system prompt válido: Langfuse no devolvió texto "
            f"usable o falló la petición, y no existe el archivo {path}."
        )
    raise AgentConfigError(
        f"No se encontró el archivo de system prompt ({path}). "
        "Configura SYSTEM_PROMPT, LANGFUSE_PROMPT_NAME con Langfuse, o crea el archivo."
    )


def fetch_prompt_from_langfuse(settings: "Settings", prompt_name: str) -> str:
    """Obtiene el texto del prompt desde Langfuse; cadena vacía si falla."""
    try:
        client = Langfuse(
            public_key=settings.langfuse_public_key.strip(),
            secret_key=settings.langfuse_secret_key.strip(),
            host=settings.langfuse_host.strip(),
            timeout=LANGFUSE_FETCH_TIMEOUT_S,
        )
        logger.info("Cargando prompt %s desde Langfuse con label %s", prompt_name, settings.langfuse_prompt_label)
        prompt = client.get_prompt(
            prompt_name,
            type="text",
            label=settings.langfuse_prompt_label,
            fetch_timeout_seconds=LANGFUSE_FETCH_TIMEOUT_S,
        )
        compiled = prompt.compile()
        if isinstance(compiled, str):
            return compiled
        return str(compiled)
    # pylint: disable-next=broad-exception-caught
    except Exception as exc:  # noqa: BLE001 — Langfuse SDK: get_prompt() documenta que propaga
        # cualquier excepción (sin tipo cerrado); la recuperación (log + "" -> fallback a
        # archivo local) es la misma sin importar el tipo de fallo. Ver "Excepciones anchas
        # justificadas" en .claude/rules/estandar-python.md.
        logger.warning(
            "No se pudo cargar el prompt desde Langfuse (name=%r): %s",
            prompt_name,
            exc,
        )
        return ""


def finalize_system_prompt(combined: str) -> str:
    """Añade el bloque ``<skills>`` al final si hay guías bajo ``skills/``."""
    skills_block = build_skills_catalog_xml()
    if not skills_block:
        return combined
    logger.info("system prompt: catálogo skills inyectado (%d chars)", len(skills_block))
    return f"{combined.rstrip()}\n\n{skills_block}"


def append_base_fragment(main_text: str, base_search_dir: Path) -> str:
    """Concatena ``base.prompt.md`` junto a ``base_search_dir`` si existe."""
    base_path = base_search_dir / BASE_PROMPT_FILENAME
    base_text = read_optional(base_path)

    if base_text:
        combined = f"{base_text}\n\n{main_text}"
        logger.debug(
            "system prompt combinado: main=%d chars + base=%d chars",
            len(main_text),
            len(base_text),
        )
        return combined

    logger.debug("system prompt solo principal: %d chars", len(main_text))
    return main_text


def read_required(path: Path) -> str:
    """Lee un archivo obligatorio. Lanza AgentConfigError si está vacío."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise AgentConfigError(f"El system prompt está vacío: {path}")
    return text


def read_optional(path: Path) -> str:
    """Lee un archivo opcional. Retorna cadena vacía si no existe."""
    if not path.exists():
        logger.debug("fragmento de prompt no encontrado (opcional): %s", path)
        return ""
    text = path.read_text(encoding="utf-8")
    logger.info("fragmento de prompt cargado: %s (%d chars)", path.name, len(text))
    return text
