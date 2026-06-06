"""Static checks for PR routing of Linux game smoke and integration tests."""

from pathlib import Path

from tests.helpers import load_module_from_repo


WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")
ROUTING_SCRIPT = Path("scripts/ci_game_test_routing.py")


def load_routing_module():
    assert ROUTING_SCRIPT.exists(), f"missing routing helper: {ROUTING_SCRIPT}"
    return load_module_from_repo("ci_game_test_routing_static", str(ROUTING_SCRIPT))


def test_docs_only_changes_skip_linux_game_smoke_and_integration():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        [
            "docs/docker-manager.md",
            "skills/server-lifecycle/SKILL.md",
            "README.md",
            "docker/README.md",
        ],
        repo_root=Path("."),
    )

    assert result["mode"] == "skip"
    assert result["smoke_scripts"] == []
    assert result["integration_tests"] == []


def test_module_only_changes_target_matching_linux_game_tests():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        ["src/gamemodules/counterstrike2.py"],
        repo_root=Path("."),
    )

    assert result["mode"] == "targeted"
    assert result["smoke_scripts"] == ["tests/smoke_tests/run_counterstrike2.sh"]
    assert result["integration_tests"] == [
        "tests/integration_tests/test_counterstrike2.py"
    ]


def test_routing_outputs_split_heavy_and_standard_game_matrices():
    routing = load_routing_module()

    outputs = routing.build_outputs_for_changed_files(
        [
            "src/gamemodules/palworld/main.py",
            "src/gamemodules/counterstrike2.py",
        ],
        repo_root=Path("."),
    )

    assert outputs["has_smoke_standard_tests"] == "true"
    assert outputs["has_smoke_heavy_tests"] == "true"
    assert outputs["has_integration_standard_tests"] == "true"
    assert outputs["has_integration_heavy_tests"] == "true"
    assert "run_counterstrike2.sh" in outputs["smoke_standard_matrix"]
    assert "run_palworld.sh" in outputs["smoke_heavy_matrix"]
    assert "test_counterstrike2.py" in outputs["integration_standard_matrix"]
    assert "test_palworld.py" in outputs["integration_heavy_matrix"]


def test_workflow_changes_force_full_linux_game_test_run():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        [".github/workflows/unittest.yaml"],
        repo_root=Path("."),
    )

    assert result["mode"] == "all"


def test_unittest_workflow_declares_classify_changes_job():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "classify-changes:" in text


def test_unittest_workflow_routes_linux_game_matrices_from_classifier_outputs():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "scripts/ci_game_test_routing.py" in text
    assert "needs: [unit-test, lint, coverage, classify-changes]" in text
    assert "needs.classify-changes.outputs.smoke_standard_matrix" in text
    assert "needs.classify-changes.outputs.smoke_heavy_matrix" in text
    assert "needs.classify-changes.outputs.integration_standard_matrix" in text
    assert "needs.classify-changes.outputs.integration_heavy_matrix" in text
    assert "if: needs.discover-smoke-tests.outputs.has_standard_tests == 'true'" in text
    assert "if: needs.discover-smoke-tests.outputs.has_heavy_tests == 'true'" in text
    assert "if: needs.discover-integration-tests.outputs.has_standard_tests == 'true'" in text
    assert "if: needs.discover-integration-tests.outputs.has_heavy_tests == 'true'" in text


def test_unittest_workflow_routes_heavy_game_jobs_to_configurable_runner_labels():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "vars.ALPHAGSM_HEAVY_RUNNER_LABELS_JSON" in text
    assert "runs-on: ${{ fromJson(vars.ALPHAGSM_HEAVY_RUNNER_LABELS_JSON || '[\"ubuntu-latest\"]') }}" in text
    assert "smoke-test-heavy:" in text
    assert "integration-test-heavy:" in text


def test_unittest_workflow_keeps_backend_and_cross_platform_jobs_unconditional():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "backend-smoke-test:" in text
    assert "backend-integration-test:" in text
    assert "windows-minecraft-integration:" in text
    assert "macos-minecraft-integration:" in text
    assert "needs: [unit-test, lint, coverage, build-integration-image]" in text
    assert "needs: [unit-test, lint, coverage]" in text
