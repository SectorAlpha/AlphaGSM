from pathlib import Path
import runpy
import sys

from server.module_catalog import load_default_module_catalog
from server.module_catalog import ModuleCatalog
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


def test_report_preserves_process_and_container_platform_declarations():
    declarations = {"process": {"platforms": ["linux"], "architectures": None},
                    "docker": {"operating_system": "linux"}}
    inventory = {"schema_version": 1, "modules": [{
        "module": "teamfortress2", "platform_requirements": declarations,
    }]}
    rows = build_module_parity_rows(
        catalog=ModuleCatalog(("teamfortress2",), {}, {}), repo_root=Path("."),
        capability_inventory=inventory,
    )
    assert rows[0].platform_requirements == declarations
    assert rows[0].platforms is None
    output = render_markdown_report(rows)
    assert "Process platforms" in output
    assert "Process architectures" in output
    assert "Docker OS" in output
    assert "| linux | unknown | linux |" in output


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


def test_parity_does_not_claim_runtime_verification_without_tracker_evidence(tmp_path):
    module_dir = tmp_path / "src" / "gamemodules"
    module_dir.mkdir(parents=True)
    (module_dir / "example.py").write_text("def get_runtime_requirements(server): pass\ndef get_container_spec(server): pass\n")
    (tmp_path / "disabled_servers.conf").write_text("")
    catalog = ModuleCatalog(("example",), {}, {})
    row = build_module_parity_rows(catalog=catalog, repo_root=tmp_path)[0]
    assert row.support_state == "UNKNOWN"
    assert row.runtime_verified is False


def test_generate_module_parity_script_bootstraps_src_path(monkeypatch):
    repo_root = Path(".").resolve()
    src_root = repo_root / "src"
    script_path = repo_root / "scripts" / "generate_module_parity_report.py"
    original_path = list(sys.path)
    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in original_path if Path(entry or ".").resolve() != src_root],
    )

    removed_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "server" or name.startswith("server.")
    }
    for name in removed_modules:
        sys.modules.pop(name, None)

    try:
        namespace = runpy.run_path(str(script_path), run_name="module_parity_bootstrap_test")
    finally:
        sys.modules.update(removed_modules)

    assert namespace["REPO_ROOT"] == repo_root
