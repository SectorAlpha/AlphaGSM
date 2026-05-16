from pathlib import Path

from server.module_catalog import load_default_module_catalog
from server.module_parity import (
    _module_source_path,
    build_module_parity_rows,
    render_json_report,
    render_markdown_report,
)


def test_build_module_parity_rows_excludes_aliases():
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=Path("."),
    )

    names = {row.canonical_id for row in rows}

    assert "teamfortress2" in names
    assert "tf2" not in names
    assert "tf2server" not in names


def test_build_module_parity_rows_flags_unimplemented_status_modules():
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=Path("."),
    )

    row = next(item for item in rows if item.canonical_id == "projectzomboid")

    assert row.contract_complete is False
    assert any("status" in reason for reason in row.missing_surfaces)


def test_render_markdown_report_includes_aliases_and_contract_columns():
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=Path("."),
    )
    output = render_markdown_report(rows[:1])

    assert (
        "| Canonical module | Aliases | Support state | Contract complete | Runtime verified |"
        in output
    )


def test_render_json_report_has_trailing_newline():
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=Path("."),
    )

    output = render_json_report(rows[:1])

    assert output.endswith("\n")


def test_checked_in_module_parity_report_matches_generated_artifacts():
    repo_root = Path(".")
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=repo_root,
    )

    assert (repo_root / "docs" / "module_parity_report.md").read_text(
        encoding="utf-8"
    ) == render_markdown_report(rows)
    assert (repo_root / "docs" / "module_parity_report.json").read_text(
        encoding="utf-8"
    ) == render_json_report(rows)


def test_build_module_parity_rows_accepts_assignment_based_runtime_hooks():
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(
        catalog=catalog,
        repo_root=Path("."),
    )

    row = next(item for item in rows if item.canonical_id == "arma3.vanilla")

    assert "runtime_requirements" not in row.missing_surfaces
    assert "container_spec" not in row.missing_surfaces


def test_module_source_path_prefers_package_init_when_present(tmp_path):
    repo_root = tmp_path
    package_dir = repo_root / "src" / "gamemodules" / "teamfortress2"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("SERVER_NAME = 'tf2'\n", encoding="utf-8")
    (package_dir / "main.py").write_text("HELPER = True\n", encoding="utf-8")
    flat_module_path = repo_root / "src" / "gamemodules" / "counterstrike2.py"
    flat_module_path.parent.mkdir(parents=True, exist_ok=True)
    flat_module_path.write_text("SERVER_NAME = 'cs2'\n", encoding="utf-8")

    assert _module_source_path(repo_root, "teamfortress2") == package_dir / "__init__.py"
    assert _module_source_path(repo_root, "counterstrike2") == flat_module_path
