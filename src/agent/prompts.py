"""Carga el prompt del agente en dos capas: system (reglas de oro) y base (comportamiento)."""

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
    """Arma el prompt del agente en dos capas, cada una con una sola fuente.

    1. **system** (reglas de oro, fijas): ``SYSTEM_PROMPT`` (inline) o el archivo
       ``SYSTEM_PROMPT_PATH`` / ``system.promt.md``. Nunca viene de Langfuse.
    2. **base** (comportamiento y guía): el prompt de Langfuse ``LANGFUSE_PROMPT_NAME`` si existe y se
       puede cargar; si no, ``base.prompt.md`` local. Nunca se usan los dos a la vez.

    El resultado es ``system`` + ``base`` + catálogo ``<skills>``. Si falta una capa en todas sus fuentes
    se lanza ``AgentConfigError`` con el detalle.
    """
    system_text = resolve_system_text(settings)
    base_text = resolve_base_text(settings)
    combined = f"{system_text.strip()}\n\n{base_text.strip()}"
    logger.info("system prompt: system=%d chars + base=%d chars", len(system_text.strip()), len(base_text.strip()))
    return finalize_system_prompt(combined)


def resolve_system_text(settings: "Settings") -> str:
    """Reglas de oro: ``SYSTEM_PROMPT`` (inline) o archivo local; nunca Langfuse."""
    inline = (settings.system_prompt_env or "").strip()
    if inline:
        logger.info("system: origen=inline (%d chars)", len(inline))
        logger.debug("Texto del system prompt inline: %s", inline)
        return inline

    path = settings.resolved_system_prompt_file()
    if not path.exists():
        raise AgentConfigError(
            f"No se encontró el archivo de system prompt ({path}). "
            "Define SYSTEM_PROMPT o crea el archivo con las reglas de oro del agente."
        )
    text = read_required(path)
    logger.info("system: origen=archivo %s (%d chars)", path.name, len(text.strip()))
    logger.debug("Texto del system prompt: %s", text.strip())
    return text


def resolve_base_text(settings: "Settings") -> str:
    """Comportamiento y guía: Langfuse si está disponible; si no, ``base.prompt.md`` local (nunca ambos)."""
    lf_name = (settings.langfuse_prompt_name or "").strip()
    if lf_name:
        fetched = fetch_prompt_from_langfuse(settings, lf_name).strip()
        if fetched:
            label = settings.langfuse_prompt_label
            logger.info("base: origen=langfuse name=%s label=%s (%d chars)", lf_name, label, len(fetched))
            logger.debug("Texto del base prompt de Langfuse: %s", fetched)
            return fetched
        logger.warning(
            "base: Langfuse no devolvió texto usable (name=%s); se usa el base local en su lugar", lf_name
        )

    base_path = settings.resolved_system_prompt_file().parent / BASE_PROMPT_FILENAME
    local = read_optional(base_path).strip()
    if not local:
        origin = f"Langfuse ({lf_name}) ni " if lf_name else ""
        raise AgentConfigError(
            f"No se pudo obtener el base prompt: ni {origin}el archivo local {base_path} tienen texto usable."
        )
    logger.info("base: origen=local %s (%d chars)", base_path.name, len(local))
    logger.debug("Texto del base prompt local: %s", local)
    return local


def fetch_prompt_from_langfuse(settings: "Settings", prompt_name: str) -> str:
    """Obtiene el texto del prompt desde Langfuse; cadena vacía si falla."""
    try:
        client = Langfuse(
            public_key=settings.langfuse_public_key.strip(),
            secret_key=settings.langfuse_secret_key.strip(),
            host=settings.langfuse_host.strip(),
            timeout=LANGFUSE_FETCH_TIMEOUT_S,
        )
        logger.debug("Cargando prompt %s desde Langfuse con label %s", prompt_name, settings.langfuse_prompt_label)
        prompt = client.get_prompt(
            prompt_name,
            type="text",
            label=settings.langfuse_prompt_label,
            fetch_timeout_seconds=LANGFUSE_FETCH_TIMEOUT_S,
        )
        logger.info(
            "Langfuse prompt obtenido: name=%s label=%s version=%s",
            prompt_name,
            settings.langfuse_prompt_label,
            getattr(prompt, "version", None),
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
            type(exc).__name__,
        )
        return ""


def finalize_system_prompt(combined: str) -> str:
    """Añade el bloque ``<skills>`` al final si hay guías bajo ``skills/``."""
    skills_block = build_skills_catalog_xml()
    if not skills_block:
        return combined
    logger.debug("system prompt: catálogo skills inyectado (%d chars)", len(skills_block))
    return f"{combined.rstrip()}\n\n{skills_block}"


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
    logger.debug("fragmento de prompt cargado: %s (%d chars)", path.name, len(text))
    return text
