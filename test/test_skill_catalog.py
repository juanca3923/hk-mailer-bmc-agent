"""Tests del catálogo de skills y lectura de guías."""

from __future__ import annotations

from pathlib import Path

from config.skill_catalog import (
    build_skills_catalog_xml,
    discover_skill_entries,
    format_skills_xml_block,
    read_skill_guide_json,
    resolve_skill_guide_path,
)


def test_build_skills_catalog_xml_empty_dir(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    assert build_skills_catalog_xml(skills_root) == ""


def test_format_skills_xml_block_empty() -> None:
    assert format_skills_xml_block([]) == ""


def test_flat_md_with_frontmatter(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "foo.md").write_text(
        "---\ndescription: guia de prueba foo\n---\n\n# Ignorado\n",
        encoding="utf-8",
    )
    xml = build_skills_catalog_xml(skills_root)
    assert xml == "<skills>\nfoo => guia de prueba foo\n</skills>"


def test_subdir_skill_md_with_h1_title(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    bar_dir = skills_root / "bar"
    bar_dir.mkdir(parents=True)
    (bar_dir / "SKILL.md").write_text("# Título bar\n\nCuerpo.\n", encoding="utf-8")
    entries = discover_skill_entries(skills_root)
    assert len(entries) == 1
    assert entries[0]["stem"] == "bar"
    assert entries[0]["description"] == "Título bar"


def test_multiple_stems_sorted(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "zeta.md").write_text("# Z\n", encoding="utf-8")
    (skills_root / "alpha.md").write_text("# A\n", encoding="utf-8")
    xml = build_skills_catalog_xml(skills_root)
    assert xml == "<skills>\nalpha => A\nzeta => Z\n</skills>"


def test_read_skill_guide_from_subdir(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    stem_dir = skills_root / "baz"
    stem_dir.mkdir(parents=True)
    (stem_dir / "SKILL.md").write_text("Contenido baz.\n", encoding="utf-8")
    result = read_skill_guide_json("baz", root=skills_root)
    assert result["ok"] is True
    assert result["content"] == "Contenido baz.\n"


def test_duplicate_stem_prefers_flat_file(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "dup.md").write_text(
        "---\ndescription: desde plano\n---\n",
        encoding="utf-8",
    )
    dup_dir = skills_root / "dup"
    dup_dir.mkdir()
    (dup_dir / "SKILL.md").write_text(
        "---\ndescription: desde carpeta\n---\n",
        encoding="utf-8",
    )
    entries = discover_skill_entries(skills_root)
    assert len(entries) == 1
    assert entries[0]["description"] == "desde plano"
    assert resolve_skill_guide_path("dup", skills_root) == (skills_root / "dup.md").resolve()
