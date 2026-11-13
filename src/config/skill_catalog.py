"""Catálogo y lectura segura de skills (guías Markdown bajo `skills/`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from config.logger import get_logger
from config.settings import skills_dir as repo_skills_dir
from constants.config import DEFAULT_MAX_SKILL_CHARS, SKILL_STEM_RE
from type_defs.models.agent.skill_catalog import SkillCatalogEntry

logger = get_logger()


def discover_skill_entries(root: Path | None = None) -> list[SkillCatalogEntry]:
    """Descubre skills bajo ``skills/*.md`` y ``skills/<dir>/SKILL.md``, ordenadas por stem."""

    def entry_from_file(stem: str, path: Path) -> SkillCatalogEntry:
        text = path.read_text(encoding="utf-8")
        return SkillCatalogEntry(stem=stem, description=extract_skill_description(text, stem))

    base = (root or repo_skills_dir()).resolve()
    if not base.is_dir():
        logger.debug("skill catalog: carpeta inexistente o no es directorio: %s", base)
        return []

    by_stem: dict[str, SkillCatalogEntry] = {}

    for path in sorted(base.glob("*.md")):
        if not path.is_file():
            continue
        stem = path.stem
        if not SKILL_STEM_RE.fullmatch(stem):
            logger.warning("skill catalog: stem inválido en archivo plano %s", path.name)
            continue
        by_stem[stem] = entry_from_file(stem, path)

    for skill_md in sorted(base.glob("*/SKILL.md")):
        if not skill_md.is_file():
            continue
        stem = skill_md.parent.name
        if not SKILL_STEM_RE.fullmatch(stem):
            logger.warning("skill catalog: stem inválido en carpeta %s", skill_md.parent.name)
            continue
        if stem in by_stem:
            logger.warning(
                "skill catalog: stem duplicado %s; se usa %s.md y se ignora %s/SKILL.md",
                stem,
                stem,
                stem,
            )
            continue
        by_stem[stem] = entry_from_file(stem, skill_md)

    return [by_stem[k] for k in sorted(by_stem)]


def format_skills_xml_block(entries: list[SkillCatalogEntry]) -> str:
    """Formatea el bloque ``<skills>``; cadena vacía si no hay entradas."""
    if not entries:
        return ""
    lines = [f"{entry['stem']} => {entry['description']}" for entry in entries]
    body = "\n".join(lines)
    return f"<skills>\n{body}\n</skills>"


def build_skills_catalog_xml(root: Path | None = None) -> str:
    """Construye el bloque XML del catálogo para inyectar al final del system prompt."""
    return format_skills_xml_block(discover_skill_entries(root))


def validate_skill_stem(raw: str) -> str | None:
    """Normaliza y valida el nombre lógico de la skill; None si es inválido."""
    name = raw.strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    if name.lower().endswith(".md"):
        name = name[:-3]
    name = name.strip()
    if not name or not SKILL_STEM_RE.fullmatch(name):
        return None
    return name


def read_skill_guide_json(
    skill_name: str,
    *,
    root: Path | None = None,
    max_chars: int = DEFAULT_MAX_SKILL_CHARS,
) -> dict[str, object]:
    """Lee una guía por stem: ``skills/<stem>.md`` o ``skills/<stem>/SKILL.md``."""
    root_resolved = (root or repo_skills_dir()).resolve()
    stem = validate_skill_stem(skill_name)
    if stem is None:
        return {
            "ok": False,
            "error": (
                "Nombre de skill inválido. Usa el stem del catálogo (ej. make_report para "
                "make_report.md o make_report/SKILL.md): letras, números, guión y guión bajo; "
                "sin rutas ni '..'"
            ),
        }

    path = resolve_skill_guide_path(stem, root_resolved)
    if path is None:
        logger.info("skill guide: archivo no encontrado stem=%s", stem)
        return {
            "ok": False,
            "error": (f"No existe la skill '{stem}' (buscado: {stem}.md y {stem}/SKILL.md en el directorio de guías)."),
        }

    text = path.read_text(encoding="utf-8")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    logger.info(
        "skill guide: leída stem=%s path=%s chars=%d truncated=%s",
        stem,
        path.name,
        len(text),
        truncated,
    )
    return {
        "ok": True,
        "skill_name": stem,
        "content": text,
        "truncated": truncated,
        "max_chars": max_chars,
    }


def read_skill_guide_json_str(
    skill_name: str,
    *,
    root: Path | None = None,
    max_chars: int = DEFAULT_MAX_SKILL_CHARS,
) -> str:
    """Serializa ``read_skill_guide_json`` a string JSON para la tool LangChain."""
    return json.dumps(read_skill_guide_json(skill_name, root=root, max_chars=max_chars), ensure_ascii=False)


def resolve_skill_guide_path(stem: str, root: Path) -> Path | None:
    """Resuelve la ruta de una guía validada; None si no existe ninguna variante permitida."""
    root_resolved = root.resolve()
    candidates = (
        (root_resolved / f"{stem}.md").resolve(),
        (root_resolved / stem / "SKILL.md").resolve(),
    )
    for path in candidates:
        try:
            path.relative_to(root_resolved)
        except ValueError:
            logger.warning("skill guide: ruta fuera de skills stem=%r path=%s", stem, path)
            return None
        if path.is_file():
            return path
    return None


def frontmatter_content_start(markdown_text: str) -> int | None:
    """Return YAML body start index after opening ``---`` line, or ``None``.

    Parameters
    ----------
    markdown_text : str
        Full Markdown file contents.

    Returns
    -------
    int or None
        Index of first frontmatter character, or ``None`` if opening delimiter is invalid.
    """
    if not markdown_text.startswith("---"):
        return None
    pos = 3
    while pos < len(markdown_text) and markdown_text[pos] in " \t":
        pos += 1
    if pos >= len(markdown_text) or markdown_text[pos] != "\n":
        return None
    return pos + 1


def try_parse_frontmatter_close(
    markdown_text: str,
    marker: int,
    content_start: int,
) -> tuple[str, str] | None:
    """If ``marker`` is a valid closing ``---`` line, return frontmatter and body.

    Parameters
    ----------
    markdown_text : str
        Full Markdown file contents.
    marker : int
        Index of ``\\n---`` found while scanning.
    content_start : int
        Start index of YAML content after the opening delimiter.

    Returns
    -------
    tuple[str, str] or None
        ``(frontmatter, body)`` when the close delimiter is well-formed; else ``None``.
    """
    close_at = marker + 1
    after_marker = close_at + 3
    while after_marker < len(markdown_text) and markdown_text[after_marker] in " \t":
        after_marker += 1
    if after_marker >= len(markdown_text) or markdown_text[after_marker] != "\n":
        return None
    return markdown_text[content_start:marker], markdown_text[after_marker + 1 :]


def split_yaml_frontmatter(markdown_text: str) -> tuple[str | None, str]:
    """Split leading YAML frontmatter from the Markdown body without backtracking regex.

    Parameters
    ----------
    markdown_text : str
        Full Markdown file contents.

    Returns
    -------
    tuple[str | None, str]
        ``(frontmatter, body)``. ``frontmatter`` is ``None`` when the document does
        not start with a well-formed ``---`` … ``---`` block.
    """
    content_start = frontmatter_content_start(markdown_text)
    if content_start is None:
        return None, markdown_text

    search_from = content_start
    while True:
        marker = markdown_text.find("\n---", search_from)
        if marker == -1:
            break
        parsed = try_parse_frontmatter_close(markdown_text, marker, content_start)
        if parsed is not None:
            return parsed[0], parsed[1]
        search_from = marker + 1

    return None, markdown_text


def description_from_frontmatter(frontmatter: str) -> str | None:
    """Read a single-line ``description:`` field from YAML frontmatter.

    Parameters
    ----------
    frontmatter : str
        Raw text between opening and closing ``---`` markers.

    Returns
    -------
    str or None
        Description value if present; otherwise ``None``.
    """
    description: str | None = None
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("description:"):
            description = stripped.split(":", 1)[1].strip()
            break
    return description


def first_h1_title(markdown_body: str) -> str | None:
    """Return the first ATX level-1 heading (``# title``) in the body.

    Parameters
    ----------
    markdown_body : str
        Markdown without frontmatter.

    Returns
    -------
    str or None
        Heading text without the leading ``#``; ``None`` if not found.
    """
    title: str | None = None
    for line in markdown_body.splitlines():
        if line.startswith("# ") and not line.startswith("##"):
            title = line[2:].strip()
            break
    return title


def extract_skill_description(markdown_text: str, stem: str) -> str:
    """Build a short catalog description for a skill Markdown file.

    Preference order: frontmatter ``description``, first ``#`` heading, then a
    stem-based fallback label.

    Parameters
    ----------
    markdown_text : str
        Full skill guide contents.
    stem : str
        Logical skill name (file stem).

    Returns
    -------
    str
        Single-line description suitable for the skills catalog.
    """

    def normalize_one_line(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())

    frontmatter, body = split_yaml_frontmatter(markdown_text)
    if frontmatter is not None:
        description = description_from_frontmatter(frontmatter)
        if description:
            return normalize_one_line(description)
    else:
        body = markdown_text

    h1_title = first_h1_title(body)
    if h1_title:
        return normalize_one_line(h1_title)

    return f"Guía {stem}"
