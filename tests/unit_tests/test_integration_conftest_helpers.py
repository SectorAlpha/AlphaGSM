"""Unit tests for integration-test helper behaviour."""

import importlib
from pathlib import Path
import subprocess
import sys
import types

import pytest
from utils.simple_kv_config import rewrite_space_config


def test_wait_for_a2s_ready_fails_even_when_tcp_is_open_and_logs_exist(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic query failure used to drive the timeout path."""

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda host, port, timeout=2.0, phase2_timeout=None: (
        (_ for _ in ()).throw(FakeQueryError("udp timeout"))
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    class _DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConn(),
    )

    log_path = tmp_path / "server.log"
    log_path.write_text("Server is hibernating\n", encoding="utf-8")

    dumped = []
    monkeypatch.setattr(
        helpers,
        "_dump_log",
        lambda path, context=None: dumped.append((path, context)),
    )

    with pytest.raises(pytest.fail.Exception, match="A2S on 127.0.0.1:27015 never responded"):
        helpers.wait_for_a2s_ready(
            "127.0.0.1",
            27015,
            5,
            log_path=log_path,
            tcp_port=27015,
        )

    assert dumped == [(log_path, "A2S timeout on port 27015")]


def test_wait_for_udp_open_retries_until_success(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic UDP reachability failure."""

    attempts = []

    def _fake_udp_ping(host, port, timeout=2.0):
        attempts.append((host, port, timeout))
        if len(attempts) < 2:
            raise FakeQueryError("udp timeout")
        return 1.5

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.udp_ping = _fake_udp_ping
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 1.0, 1.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 1.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    helpers.wait_for_udp_open("127.0.0.1", 27015, 5)

    assert len(attempts) == 2


def test_wait_for_log_marker_dumps_runtime_logs_when_context_provided(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    dumped_runtime = []
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda env, server_name, lines=200: dumped_runtime.append((env, server_name, lines)),
    )
    monkeypatch.setattr(helpers, "_dump_log", lambda path, context=None: None)

    missing_log = tmp_path / "missing.log"

    with pytest.raises(pytest.fail.Exception, match="Log never showed readiness markers"):
        helpers.wait_for_log_marker(
            missing_log,
            ["ready"],
            5,
            env={"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            server_name="ittestserver",
        )

    assert dumped_runtime == [({"ALPHAGSM_CONFIG_LOCATION": "dummy"}, "ittestserver", 200)]


def test_wait_for_glob_log_marker_dumps_runtime_logs_when_context_provided(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    dumped_runtime = []
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda env, server_name, lines=200: dumped_runtime.append((env, server_name, lines)),
    )
    monkeypatch.setattr(helpers, "_dump_log", lambda path, context=None: None)

    with pytest.raises(pytest.fail.Exception, match="Log never showed readiness markers"):
        helpers.wait_for_glob_log_marker(
            tmp_path,
            "*.log",
            ["ready"],
            5,
            env={"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            server_name="itglobserver",
        )

    assert dumped_runtime == [({"ALPHAGSM_CONFIG_LOCATION": "dummy"}, "itglobserver", 200)]


def test_run_and_assert_ok_dumps_runtime_logs_for_failed_lifecycle_command(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    failure = subprocess.CompletedProcess(
        args=["alphagsm", "itreturntomo", "query"],
        returncode=1,
        stdout="",
        stderr="Server does not appear to be responding",
    )
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    dumped_runtime = []

    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: failure)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "skip_for_known_steamcmd_issue",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda actual_env, server_name, lines=200: dumped_runtime.append(
            (actual_env, server_name, lines)
        ),
    )

    with pytest.raises(AssertionError, match="does not appear to be responding"):
        helpers.run_and_assert_ok(env, "itreturntomo", "query")

    assert dumped_runtime == [(env, "itreturntomo", 200)]


def test_build_integration_tmp_path_uses_work_dir(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(tmp_path))

    class _Factory:
        def mktemp(self, name):
            raise AssertionError("mktemp should not be used when ALPHAGSM_WORK_DIR is set")

    result = helpers.build_integration_tmp_path("armarserver", _Factory())

    assert result.parent == tmp_path / "pytest-integration"
    assert result.name.startswith("armarserver-")
    assert result.is_dir()


def test_build_integration_tmp_path_uses_default_work_root(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("ALPHAGSM_WORK_DIR", raising=False)
    monkeypatch.setattr(helpers, "DEFAULT_INTEGRATION_WORK_DIR", tmp_path / "shared-work")

    class _Factory:
        def mktemp(self, name):
            raise AssertionError("mktemp should not be used when a default work root exists")

    result = helpers.build_integration_tmp_path("ndserver", _Factory())

    assert result.parent == tmp_path / "shared-work" / "pytest-integration"
    assert result.name.startswith("ndserver-")
    assert result.is_dir()


def test_format_logged_command_redacts_secret_set_values():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    rendered = helpers._format_logged_command(  # pylint: disable=protected-access
        "alphagsm",
        ("ittestlif", "set", "db_password", "hunter2"),
    )

    assert rendered == "alphagsm ittestlif set db_password <redacted>"


def test_format_logged_command_redacts_inline_secret_assignment_flags():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    rendered = helpers._format_logged_command(  # pylint: disable=protected-access
        "alphagsm",
        ("ittestlif", "start", "--db-password=hunter2", "token=abc123"),
    )

    assert rendered == "alphagsm ittestlif start --db-password=<redacted> token=<redacted>"


def test_redact_logged_text_masks_secret_values_in_common_output_shapes():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(  # pylint: disable=protected-access
        '\n'.join(
            (
                'db_password=hunter2',
                '"token": "abc123"',
                'rcon_password supersecret',
                '--db-password=hunter2',
            )
        )
    )

    assert "hunter2" not in redacted
    assert "abc123" not in redacted
    assert "supersecret" not in redacted
    assert redacted.count("<redacted>") >= 4


def test_log_command_result_redacts_secret_values_from_stdout_and_stderr(capsys):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=1,
        stdout='db_password=hunter2\n"token": "abc123"\n',
        stderr='rcon_password supersecret\n',
    )

    helpers.log_command_result(
        "alphagsm",
        result,
        command_args=("ittestlif", "set", "db_password", "hunter2"),
    )

    captured = capsys.readouterr().out
    assert "=== alphagsm ===" in captured
    assert "hunter2" not in captured
    assert "abc123" not in captured
    assert "supersecret" not in captured
    assert captured.count("<redacted>") >= 3


def test_write_config_keeps_downloads_inside_test_home_by_default(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"

    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(tmp_path / "shared-work"))
    monkeypatch.delenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", raising=False)

    helpers.write_config(config_path, home_dir)

    text = config_path.read_text(encoding="utf-8")
    assert f"db_path = {home_dir / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {home_dir / 'downloads' / 'downloads'}" in text
    assert "[runtime]" in text
    assert "backend = process" in text


def test_write_config_can_use_shared_download_cache_when_opted_in(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"
    shared_root = tmp_path / "shared-work"

    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(shared_root))
    monkeypatch.setenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", "1")

    helpers.write_config(config_path, home_dir)

    text = config_path.read_text(encoding="utf-8")
    assert f"db_path = {shared_root / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {shared_root / 'downloads' / 'downloads'}" in text
    assert "[runtime]" in text
    assert "backend = process" in text


def test_parse_recommended_port_overrides_reads_full_claim_set():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    parsed = helpers._parse_recommended_port_overrides(
        "Port conflicts detected\n"
        "Recommended free port set: port=42270 queryport=27016 peerport=27017\n"
    )

    assert parsed == {
        "port": 42270,
        "queryport": 27016,
        "peerport": 27017,
    }


def test_port_free_for_both_probes_loopback_and_wildcard(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    binds = []

    class _FakeSocket:
        def __init__(self, _family, socktype):
            self.socktype = socktype

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self, address):
            binds.append((self.socktype, address))

    monkeypatch.setattr(helpers.socket, "socket", _FakeSocket)

    assert helpers._port_free_for_both(25565) is True
    assert binds == [
        (helpers.socket.SOCK_STREAM, ("127.0.0.1", 25565)),
        (helpers.socket.SOCK_STREAM, ("0.0.0.0", 25565)),
        (helpers.socket.SOCK_DGRAM, ("127.0.0.1", 25565)),
        (helpers.socket.SOCK_DGRAM, ("0.0.0.0", 25565)),
    ]


def test_set_source_hibernation_preserves_line_boundaries_when_appending(tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    server_cfg = tmp_path / "server.cfg"
    server_cfg.write_text('hostname "AlphaGSM IOSoccer"', encoding="utf-8")

    helpers.set_source_hibernation(server_cfg, enabled=True)

    assert server_cfg.read_text(encoding="utf-8") == (
        'hostname "AlphaGSM IOSoccer"\n'
        "sv_hibernate_when_empty 1\n"
    )


def test_iosserver_hibernation_and_rewrite_sequence_keeps_lines_separate(tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    server_cfg = tmp_path / "server.cfg"
    server_cfg.write_text(
        'exec shared_server.cfg\n\nhostname "IOSoccer Dedicated Server"',
        encoding="utf-8",
    )

    helpers.set_source_hibernation(server_cfg, enabled=True)
    rewrite_space_config(
        server_cfg,
        {
            "hostname": '"AlphaGSM IOSoccer"',
            "rcon_password": '""',
            "sv_password": '""',
        },
    )

    assert server_cfg.read_text(encoding="utf-8") == (
        "exec shared_server.cfg\n"
        "\n"
        'hostname "AlphaGSM IOSoccer"\n'
        "sv_hibernate_when_empty 1\n"
        'rcon_password ""\n'
        'sv_password ""\n'
    )


def test_module_uses_explicit_docker_runtime_for_custom_test_module():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    assert helpers._module_uses_explicit_docker_runtime(  # pylint: disable=protected-access
        "portprobe",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )


def test_module_uses_explicit_docker_runtime_returns_false_when_module_load_fails(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_load_runtime_module",
        lambda module_name, servermodulespackage="gamemodules.": (_ for _ in ()).throw(
            ImportError("boom")
        ),
    )

    assert not helpers._module_uses_explicit_docker_runtime("missing-module")  # pylint: disable=protected-access


def test_run_setup_with_port_retry_applies_recommended_nonprimary_claims(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    calls = []
    setup_failure = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=1,
        stdout="",
        stderr=(
            "Port conflicts detected:\n"
            "- unmanaged: Live listener already holds 0.0.0.0:27015\n"
            "Recommended free port set: port=42270 queryport=27016\n"
        ),
    )
    set_success = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=0,
        stdout="Value set\n",
        stderr="",
    )
    setup_success = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=0,
        stdout="Setup complete\n",
        stderr="",
    )
    responses = iter([setup_failure, set_success, setup_success])

    def _fake_run_alphagsm(env, *command_parts, timeout=None):
        calls.append(command_parts)
        return next(responses)

    monkeypatch.setattr(helpers, "run_alphagsm", _fake_run_alphagsm)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(helpers, "skip_for_known_steamcmd_issue", lambda result: None)
    monkeypatch.setattr(helpers, "pick_free_tcp_port", lambda: 49999)

    result, port = helpers.run_setup_with_port_retry(
        {"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
        "itblackwake",
        42267,
        tmp_path / "server",
    )

    assert result.returncode == 0
    assert port == 42270
    assert calls == [
        ("itblackwake", "setup", "-n", "42267", str(tmp_path / "server")),
        ("itblackwake", "set", "queryport", "27016"),
        ("itblackwake", "setup", "-n", "42270", str(tmp_path / "server")),
    ]


def test_run_setup_with_port_retry_forwards_known_steamcmd_flake_app_id(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    setup_failure = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=3,
        stdout="Error! App '294420' state is 0x202 after update job.\n",
        stderr="",
    )

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        lambda env, *command_parts, timeout=None: setup_failure,
    )
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(pytest.skip.Exception, match=r"app 294420"):
        helpers.run_setup_with_port_retry(
            {"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
            "it7dtd",
            26900,
            tmp_path / "server",
            steam_app_id=294420,
        )


def test_backend_write_java_wrapper_prefers_java_home(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.backend_integration_tests.conftest")
    java_home = tmp_path / "jdk-25"
    java_bin = java_home / "bin"
    java_bin.mkdir(parents=True)
    java_path = java_bin / "java"
    java_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    java_path.chmod(0o755)
    wrapper_path = tmp_path / "java-wrapper.sh"

    monkeypatch.setenv("JAVA_HOME", str(java_home))
    monkeypatch.setattr(helpers.shutil, "which", lambda name: "/usr/bin/java")

    helpers._write_java_wrapper(wrapper_path, "-Xms256M", "-Xmx768M")

    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert str(java_path) in wrapper_text
    assert "/usr/bin/java" not in wrapper_text


def test_backend_write_java_wrapper_falls_back_to_path(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.backend_integration_tests.conftest")
    wrapper_path = tmp_path / "java-wrapper.sh"

    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.setattr(helpers.shutil, "which", lambda name: "/opt/java/bin/java")

    helpers._write_java_wrapper(wrapper_path, "-Xms256M", "-Xmx768M")

    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert "/opt/java/bin/java" in wrapper_text


def test_skip_for_known_steamcmd_issue_skips_only_for_missing_configuration_0x202():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_skips_for_known_bare_state_202_flake_app():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '232130' state is 0x202 after update job.",
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=232130)


def test_skip_for_known_steamcmd_issue_skips_for_sevendaystodie_bare_state_202_flake():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '294420' state is 0x202 after update job.",
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=294420)


def test_skip_for_known_steamcmd_issue_skips_for_new_known_bare_state_202_flake_apps():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    for app_id in (346680, 746200):
        result = types.SimpleNamespace(
            stdout=f"Error! App '{app_id}' state is 0x202 after update job.",
            stderr="",
        )

        with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
            helpers.skip_for_known_steamcmd_issue(result, app_id=app_id)


def test_skip_for_known_steamcmd_issue_does_not_skip_other_steamcmd_failures():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! Timed out waiting for download chunks.",
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_does_not_skip_unknown_bare_state_202_app():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '317670' state is 0x202 after update job.",
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_does_not_skip_when_app_id_does_not_match():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=222860)


def test_skip_for_known_steamcmd_issue_does_not_skip_without_app_id():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result)


@pytest.mark.parametrize("marker", ["ENABLED (BYO):", "ENABLED (AUTH):"])
def test_skip_for_known_steamcmd_issue_skips_for_supported_prerequisite_states(marker):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["steamcmd"],
        returncode=1,
        stdout="",
        stderr=f"Error running Command\n{marker} prerequisite not available in CI\n",
    )

    with pytest.raises(pytest.skip.Exception, match="Setup skipped"):
        helpers.skip_for_known_steamcmd_issue(result)
