from pathlib import Path

from server.module_catalog import load_default_module_catalog
from server.module_parity import (
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
