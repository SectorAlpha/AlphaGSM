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


def test_long_container_integration_changes_route_to_heavy_matrix():
    routing = load_routing_module()

    outputs = routing.build_outputs_for_changed_files(
        [
            "src/gamemodules/sniperelite4server/main.py",
            "src/gamemodules/sonsoftheforestserver/main.py",
        ],
        repo_root=Path("."),
    )

    assert outputs["has_integration_standard_tests"] == "false"
    assert outputs["has_integration_heavy_tests"] == "true"
    assert "test_sniperelite4server.py" in outputs["integration_heavy_matrix"]
    assert "test_sonsoftheforestserver.py" in outputs["integration_heavy_matrix"]


def test_source_family_backlog_contains_tf2_and_counterstrike2():
    routing = load_routing_module()

    backlog = routing.docker_enablement_backlog_tests(repo_root=Path("."))

    assert "tests/integration_tests/test_tf2.py" in backlog
    assert "tests/integration_tests/test_counterstrike2.py" in backlog


def test_source_shared_batch_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_cssserver.py",
        "tests/integration_tests/test_dodsserver.py",
        "tests/integration_tests/test_hl2dmserver.py",
        "tests/integration_tests/test_nmrihserver.py",
    ):
        assert test_path not in backlog


def test_goldsrc_batch_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_bdserver.py",
        "tests/integration_tests/test_csserver.py",
        "tests/integration_tests/test_csczserver.py",
        "tests/integration_tests/test_dmcserver.py",
        "tests/integration_tests/test_dodserver.py",
        "tests/integration_tests/test_hldmserver.py",
    ):
        assert test_path not in backlog


def test_source_shared_batch_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        [
            "tests/integration_tests/test_cssserver.py",
            "tests/integration_tests/test_dodsserver.py",
            "tests/integration_tests/test_hl2dmserver.py",
            "tests/integration_tests/test_nmrihserver.py",
        ],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_cssserver.py",
            "label": "cssserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_cssserver.py",
            "label": "cssserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 3,
            "files": "tests/integration_tests/test_dodsserver.py",
            "label": "dodsserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 4,
            "files": "tests/integration_tests/test_dodsserver.py",
            "label": "dodsserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 5,
            "files": "tests/integration_tests/test_hl2dmserver.py",
            "label": "hl2dmserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 6,
            "files": "tests/integration_tests/test_hl2dmserver.py",
            "label": "hl2dmserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 7,
            "files": "tests/integration_tests/test_nmrihserver.py",
            "label": "nmrihserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 8,
            "files": "tests/integration_tests/test_nmrihserver.py",
            "label": "nmrihserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_goldsrc_batch_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        [
            "tests/integration_tests/test_bdserver.py",
            "tests/integration_tests/test_csserver.py",
            "tests/integration_tests/test_csczserver.py",
            "tests/integration_tests/test_dmcserver.py",
            "tests/integration_tests/test_dodserver.py",
            "tests/integration_tests/test_hldmserver.py",
        ],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bdserver.py",
            "label": "bdserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bdserver.py",
            "label": "bdserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 3,
            "files": "tests/integration_tests/test_csczserver.py",
            "label": "csczserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 4,
            "files": "tests/integration_tests/test_csczserver.py",
            "label": "csczserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 5,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 6,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 7,
            "files": "tests/integration_tests/test_dmcserver.py",
            "label": "dmcserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 8,
            "files": "tests/integration_tests/test_dmcserver.py",
            "label": "dmcserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 9,
            "files": "tests/integration_tests/test_dodserver.py",
            "label": "dodserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 10,
            "files": "tests/integration_tests/test_dodserver.py",
            "label": "dodserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 11,
            "files": "tests/integration_tests/test_hldmserver.py",
            "label": "hldmserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 12,
            "files": "tests/integration_tests/test_hldmserver.py",
            "label": "hldmserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_csserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_csserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_goldsrc_dual_lane_files_keep_process_runtime_fallback():
    for path in (
        Path("tests/integration_tests/test_bdserver.py"),
        Path("tests/integration_tests/test_csserver.py"),
        Path("tests/integration_tests/test_csczserver.py"),
        Path("tests/integration_tests/test_dmcserver.py"),
        Path("tests/integration_tests/test_dodserver.py"),
        Path("tests/integration_tests/test_hldmserver.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' in text


def test_dual_lane_subset_stays_separate_from_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))
    dual_lane = set(routing.PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS)

    assert backlog.isdisjoint(dual_lane)


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
