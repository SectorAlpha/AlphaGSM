from tests.helpers import load_module_from_repo


matrix = load_module_from_repo(
    "backend_docker_family_matrix",
    "tests/backend_integration_tests/docker_family_matrix.py",
)


def test_docker_backend_family_matrix_declares_three_cases_per_runtime_family():
    counts = {}
    for case in matrix.all_cases():
        counts[case.runtime_family] = counts.get(case.runtime_family, 0) + 1

    assert counts == {
        "java": 3,
        "quake-linux": 3,
        "service-console": 3,
        "simple-tcp": 3,
        "steamcmd-linux": 3,
        "wine-proton": 3,
    }


def test_docker_backend_family_matrix_active_cases_are_ci_ready_java_lifecycle_cases():
    active = matrix.active_cases()

    assert [case.slug for case in active] == [
        "java-minecraft-vanilla",
        "java-minecraft-paper",
        "java-minecraft-velocity",
    ]
    for case in active:
        assert case.runtime_family == "java"
        assert case.status == "active"
        assert case.validator == "minecraft-status"
        assert case.query_marker
        assert case.info_marker
        assert case.info_protocol == "slp"
        assert case.setup_profile
