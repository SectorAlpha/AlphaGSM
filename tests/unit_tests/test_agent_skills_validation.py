"""Validate real metadata, reference, catalogue and discovery failure modes."""

import runpy
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate_agent_skills.py"


@pytest.fixture
def validator():
    return runpy.run_path(str(SCRIPT), run_name="agent_skills_validation")


def make_skill(root, name="example", metadata=None, body="# Example\n"):
    folder = root / "skills" / name
    folder.mkdir(parents=True, exist_ok=True)
    if metadata is None:
        metadata = f"name: {name}\ndescription: Use when testing a skill.\n"
    manifest = folder / "SKILL.md"
    manifest.write_text(f"---\n{metadata}---\n{body}", encoding="utf-8")
    discovery = root / ".agents/skills" / name
    discovery.parent.mkdir(parents=True, exist_ok=True)
    try:
        discovery.symlink_to(f"../../skills/{name}", target_is_directory=True)
    except OSError:
        # Windows checkouts without symlink permission still support explicit loading.
        discovery.write_text(f"../../skills/{name}", encoding="utf-8")
    catalogue = root / "SKILLS.md"
    with catalogue.open("a", encoding="utf-8") as stream:
        stream.write(f"- [{name}](skills/{name}/SKILL.md)\n")
    return manifest, discovery


def test_valid_library_with_folded_yaml_and_local_reference(tmp_path, validator):
    manifest, _ = make_skill(
        tmp_path,
        metadata="name: example\ndescription: >-\n  Use when testing\n  a skill.\n",
        body="# Example\n[Reference](references/context.md#example)\n"
             "[Docs](https://example.com)\n",
    )
    reference = manifest.parent / "references/context.md"
    reference.parent.mkdir()
    reference.write_text("# Example\n", encoding="utf-8")
    assert validator["validate"](tmp_path) == []


@pytest.mark.parametrize("metadata, expected", [
    ("name: example\n", "description"),
    ("name: example\ndescription: ''\n", "description"),
    ("name: example\ndescription: []\n", "description"),
    ("name: Different\ndescription: Test.\n", "name"),
    ("name: another\ndescription: Test.\n", "directory"),
    ("name: example\nname: example\ndescription: Test.\n", "duplicate YAML key"),
    ("name: [\n", "YAML"),
    ("- example\n", "mapping"),
])
def test_invalid_metadata(tmp_path, validator, metadata, expected):
    make_skill(tmp_path, metadata=metadata)
    assert expected in "\n".join(validator["validate"](tmp_path))


def test_missing_frontmatter(tmp_path, validator):
    manifest, _ = make_skill(tmp_path)
    manifest.write_text("# No metadata\n", encoding="utf-8")
    assert "frontmatter" in "\n".join(validator["validate"](tmp_path))


def test_duplicate_names(tmp_path, validator):
    make_skill(tmp_path)
    make_skill(tmp_path, "second", "name: example\ndescription: Test.\n")
    assert "duplicate skill name" in "\n".join(validator["validate"](tmp_path))


def test_missing_manifest_is_not_silently_ignored(tmp_path, validator):
    make_skill(tmp_path)
    (tmp_path / "skills/incomplete").mkdir()
    assert "incomplete/SKILL.md" in "\n".join(validator["validate"](tmp_path))


def test_broken_reference_in_supporting_document(tmp_path, validator):
    manifest, _ = make_skill(tmp_path)
    reference = manifest.parent / "references/context.md"
    reference.parent.mkdir()
    reference.write_text("[Missing](gone.md)\n", encoding="utf-8")
    assert "gone.md" in "\n".join(validator["validate"](tmp_path))


def test_missing_discovery_link(tmp_path, validator):
    _, link = make_skill(tmp_path)
    link.unlink()
    assert "discovery" in "\n".join(validator["validate"](tmp_path))


def test_wrong_discovery_target(tmp_path, validator):
    _, link = make_skill(tmp_path)
    link.unlink()
    try:
        link.symlink_to(tmp_path.parent)
    except OSError:
        link.write_text("../../outside", encoding="utf-8")
    assert "discovery" in "\n".join(validator["validate"](tmp_path))


def test_git_symlink_stub_allows_explicit_loading(tmp_path, validator, capsys):
    _, link = make_skill(tmp_path)
    link.unlink()
    link.write_text("../../skills/example", encoding="utf-8")
    assert validator["main"](["--repo-root", str(tmp_path)]) == 0
    assert "explicit loading" in capsys.readouterr().out


def test_unindexed_skill_and_stale_catalogue(tmp_path, validator):
    make_skill(tmp_path)
    (tmp_path / "SKILLS.md").write_text(
        "[Gone](skills/gone/SKILL.md)\n", encoding="utf-8"
    )
    errors = "\n".join(validator["validate"](tmp_path))
    assert "catalogue" in errors
    assert "gone/SKILL.md" in errors


def test_reference_escaping_repository(tmp_path, validator):
    make_skill(tmp_path, body="[Outside](../../../outside.md)\n")
    assert "outside repository" in "\n".join(validator["validate"](tmp_path))


def test_empty_library_fails_cli(tmp_path, validator, capsys):
    assert validator["main"](["--repo-root", str(tmp_path)]) == 1
    assert "no skills" in capsys.readouterr().out


@pytest.mark.parametrize("body", [
    "[Self](SKILL.md 'Context')\n",
    "~~~markdown\n[Illustration](not-a-real-file.md)\n~~~\n",
    "````markdown\n[Illustration](not-a-real-file.md)\n````\n",
])
def test_valid_markdown_titles_and_fenced_examples(tmp_path, validator, body):
    make_skill(tmp_path, body=body)
    assert validator["validate"](tmp_path) == []


def test_malformed_link_is_a_diagnostic(tmp_path, validator):
    make_skill(tmp_path, body="[Bad](http://[broken)\n")
    assert "invalid Markdown URL" in "\n".join(validator["validate"](tmp_path))


def test_real_library(validator):
    assert validator["validate"](SCRIPT.parents[1]) == []
