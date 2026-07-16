"""Static contract tests for integration test files."""

import re
import runpy
from pathlib import Path


INTEGRATION_TEST_DIR = Path("tests/integration_tests")
DISABLED_SERVERS_PATH = Path("disabled_servers.conf")
SPECIAL_CASES = {"test_archive_backed_installs.py"}
SS14_INTEGRATION_TEST = INTEGRATION_TEST_DIR / "test_ss14server.py"
RUNTIME_AWARE_PROTOCOL_TESTS = {
    "test_palworld.py": "udp",
    "test_btserver.py": "udp",
    "test_rust.py": "a2s",
    "test_valheim.py": "udp",
    "test_sniperelite4server.py": "udp",
    "test_sonsoftheforestserver.py": "a2s",
    "test_ricochetserver.py": "a2s",
    "test_bmdmserver.py": "a2s",
    "test_empyrionserver.py": "tcp",
    "test_readyornotserver.py": "udp",
    "test_reignofdwarfserver.py": "a2s",
    "test_remnantsserver.py": "a2s",
    "test_returntomoriaserver.py": "udp",
    "test_bdserver.py": "a2s",
    "test_blackops3server.py": "udp",
    "test_mythofempiresserver.py": "a2s",
    "test_nightingale.py": "http_status",
    "test_xntserver.py": "quake",
}


def _integration_test_files():
    return sorted(
        path
        for path in INTEGRATION_TEST_DIR.glob("test_*.py")
        if path.name not in SPECIAL_CASES
    )


def _disabled_module_names():
    names = []
    for raw_line in DISABLED_SERVERS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        names.append(line.split("\t", 1)[0].strip())
    return sorted(names)


def test_disabled_modules_have_matching_integration_test_files():
    offenders = []
    for module_name in _disabled_module_names():
        expected = INTEGRATION_TEST_DIR / ("test_" + module_name.replace(".", "_") + ".py")
        if not expected.is_file():
            offenders.append(f"{module_name}: missing {expected}")

    assert offenders == []


def test_integration_tests_do_not_allow_tcp_fallback_output():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if 'or "Server port is open" in query_result.stdout' in text:
            offenders.append(f"{path}: query fallback")
        if 'or "Server port is open" in info_result.stdout' in text:
            offenders.append(f"{path}: info fallback")

    assert offenders == []


def test_integration_tests_require_exact_protocol_assertions():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if '_info_data["protocol"] in (' in text:
            offenders.append(str(path))

    assert offenders == []


def test_integration_tests_do_not_soft_pass_query_info_commands():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "if query_result.returncode == 0:" in text:
            offenders.append(f"{path}: query")
        if "if info_result.returncode == 0:" in text:
            offenders.append(f"{path}: info")
        if "if info_json_result.returncode == 0:" in text:
            offenders.append(f"{path}: info-json")

    assert offenders == []


def test_a2s_integration_tests_do_not_accept_hibernation_as_success():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "wait_for_a2s_ready" in text and "Server is hibernating" in text:
            offenders.append(str(path))

    assert offenders == []


def test_runtime_aware_integration_tests_use_alphagsm_info_surface_only():
    offenders = []
    for filename, protocol in RUNTIME_AWARE_PROTOCOL_TESTS.items():
        path = INTEGRATION_TEST_DIR / filename
        text = path.read_text(encoding="utf-8")
        if f'"{protocol}"' not in text or "wait_for_info_protocol" not in text:
            offenders.append(f"{path}: missing {protocol} info readiness")
        if "wait_for_a2s_ready(" in text:
            offenders.append(f"{path}: raw A2S readiness")
        if "detect_query_host" in text:
            offenders.append(f"{path}: guessed query host")

    assert offenders == []


def test_blackops3_generic_udp_query_assertion_matches_alphagsm_output():
    text = (INTEGRATION_TEST_DIR / "test_blackops3server.py").read_text(
        encoding="utf-8"
    )

    assert '"Server port is open (UDP ping on port" in query_result.stdout' in text
    assert '"Server is responding" in query_result.stdout' not in text


def test_rust_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_rust.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_ricochet_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_ricochetserver.py").read_text(
        encoding="utf-8"
    )

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_bmdmserver_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_bmdmserver.py").read_text(
        encoding="utf-8"
    )

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_bdserver_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_bdserver.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_proton_docker_tests_do_not_require_host_only_readiness_surfaces():
    for filename in (
        "test_empyrionserver.py",
        "test_mythofempiresserver.py",
        "test_reignofdwarfserver.py",
        "test_remnantsserver.py",
    ):
        text = (INTEGRATION_TEST_DIR / filename).read_text(encoding="utf-8")

        assert "wait_for_info_protocol" in text
        assert "wait_for_log_marker" not in text


def test_xonotic_uses_alphagsm_info_instead_of_raw_quake_readiness():
    text = (INTEGRATION_TEST_DIR / "test_xntserver.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_quake_ready" not in text


def test_docker_lanes_require_docker_directly():
    routing = runpy.run_path("scripts/ci_game_test_routing.py")
    docker_default_tests = routing["DOCKER_DEFAULT_RUNTIME_TESTS"]
    offenders = []
    for test_path in sorted(docker_default_tests):
        path = Path(test_path)
        if path.name in SPECIAL_CASES:
            continue
        text = path.read_text(encoding="utf-8")
        if 'require_command("docker")' not in text:
            offenders.append(f"{path}: missing direct Docker requirement")
        if re.search(r"require_command_for_runtime\(\s*[\"']docker[\"']", text):
            offenders.append(f"{path}: Docker passed to process-only helper")

    assert offenders == []


def test_readyornot_uses_game_log_and_current_udp_health_surface():
    integration_text = (INTEGRATION_TEST_DIR / "test_readyornotserver.py").read_text(
        encoding="utf-8"
    )
    smoke_text = Path("tests/smoke_tests/run_readyornotserver.sh").read_text(
        encoding="utf-8"
    )

    assert '"ReadyOrNot" / "Saved" / "Logs" / "ReadyOrNot.log"' in integration_text
    assert "wait_for_log_marker" in integration_text
    assert 'wait_for_info_protocol(env, server_name, "udp"' in integration_text
    assert '"a2s"' not in integration_text
    assert "ReadyOrNot/Saved/Logs/ReadyOrNot.log" in smoke_text
    assert 'wait_for_info_protocol "$SERVER_NAME" "udp"' in smoke_text
    assert '"a2s"' not in smoke_text


def test_returntomoria_uses_alphagsm_info_instead_of_raw_udp_readiness():
    text = (INTEGRATION_TEST_DIR / "test_returntomoriaserver.py").read_text(
        encoding="utf-8"
    )

    assert "wait_for_info_protocol" in text
    assert "wait_for_udp_open" not in text


def test_iosserver_lifecycle_is_gated_on_provider_authentication():
    text = (INTEGRATION_TEST_DIR / "test_iosserver.py").read_text(
        encoding="utf-8"
    )

    assert "pytest.mark.skip" in text
    assert "ENABLED (AUTH)" in text


def test_integration_tests_do_not_permanently_skip_download_or_timeout_failures():
    """Download and timeout failures must remain visible to CI."""

    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if re.search(r"pytest\.mark\.skip[^\n]*(download|timeout)", text, re.IGNORECASE):
            offenders.append(str(path))

    assert offenders == []


def test_ss14_integration_supports_byo_archive_url_without_hiding_download_failures():
    text = SS14_INTEGRATION_TEST.read_text(encoding="utf-8")

    assert "ALPHAGSM_SS14_SERVER_URL" in text
    assert "BYO_SKIP_REASON" in text
    assert "skip_for_known_steamcmd_issue(result)" in text
    assert 'pytest.mark.skip' not in text
