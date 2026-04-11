"""Cheap backend integration coverage for the server port manager."""

import json
import subprocess

import pytest

pytestmark = pytest.mark.backend_integration

PROCESS_SERVER_MODULE = "portprobe"
DOCKER_TEST_IMAGE = "python:3.11-alpine"
START_TIMEOUT = 20
STOP_TIMEOUT = 20


def _assert_query_and_info(lifecycle, env, server_name, expected_port):
    query_result = lifecycle.run_and_assert_ok(env, server_name, "query")
    assert "Server port is open" in query_result.stdout
    assert str(expected_port) in query_result.stdout

    info_result = lifecycle.run_and_assert_ok(env, server_name, "info")
    assert "Server port is open" in info_result.stdout
    assert str(expected_port) in info_result.stdout

    info_json_result = lifecycle.run_and_assert_ok(env, server_name, "info", "--json")
    info_data = json.loads(info_json_result.stdout.strip())
    assert info_data["protocol"] == "tcp"
    assert info_data["port"] == expected_port


def test_port_manager_setup_auto_shift_lifecycle_process(tmp_path, lifecycle):
    """Setup should auto-shift a default-owned port group, then still run normally."""

    lifecycle.require_backend_opt_in()

    home_dir = tmp_path / "alphagsm-home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"
    anchor_dir = tmp_path / "anchor"
    shifted_dir = tmp_path / "shifted"

    base_port = lifecycle.pick_free_tcp_port()
    lifecycle.write_config(
        config_path,
        home_dir,
        "BkPort#",
        backend="subprocess",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )
    env = lifecycle.alphagsm_env(config_path)
    env["ALPHAGSM_PORTPROBE_DEFAULT_PORT"] = str(base_port)
    env["ALPHAGSM_PORTPROBE_DEFAULT_QUERYPORT"] = str(base_port + 1)
    env["ALPHAGSM_PORTPROBE_DEFAULT_METRICSPORT"] = str(base_port + 2)

    lifecycle.run_and_assert_ok(env, "pm-anchor", "create", PROCESS_SERVER_MODULE)
    lifecycle.run_and_assert_ok(
        env,
        "pm-anchor",
        "setup",
        "-n",
        str(anchor_dir),
    )

    lifecycle.run_and_assert_ok(env, "pm-shift", "create", PROCESS_SERVER_MODULE)
    setup_result = lifecycle.run_and_assert_ok(
        env,
        "pm-shift",
        "setup",
        "-n",
        str(shifted_dir),
    )
    assert "shifted claimed port set" in setup_result.stdout

    shifted_data = lifecycle.load_server_data(home_dir, "pm-shift")
    assert shifted_data["port"] == base_port + 3
    assert shifted_data["queryport"] == base_port + 4
    assert shifted_data["metricsport"] == base_port + 5
    assert shifted_data["port_claim_policy"] == {
        "port": "default",
        "queryport": "default",
        "metricsport": "default",
    }

    try:
        lifecycle.run_and_assert_ok(env, "pm-shift", "start")
        lifecycle.wait_for_tcp_open("127.0.0.1", shifted_data["port"], START_TIMEOUT)
        _assert_query_and_info(lifecycle, env, "pm-shift", shifted_data["port"])
    finally:
        lifecycle.run_alphagsm(env, "pm-shift", "stop", timeout=120)
        lifecycle.wait_for_closed("127.0.0.1", shifted_data["port"], STOP_TIMEOUT)


def test_port_manager_rejects_explicit_set_collision_but_server_still_runs(tmp_path, lifecycle):
    """A colliding explicit set should fail and leave the existing lifecycle usable."""

    lifecycle.require_backend_opt_in()

    home_dir = tmp_path / "alphagsm-home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"
    anchor_dir = tmp_path / "anchor"
    target_dir = tmp_path / "target"

    base_port = lifecycle.pick_free_tcp_port()
    target_port = base_port + 10
    lifecycle.write_config(
        config_path,
        home_dir,
        "BkPort#",
        backend="subprocess",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )
    env = lifecycle.alphagsm_env(config_path)

    lifecycle.run_and_assert_ok(env, "pm-set-anchor", "create", PROCESS_SERVER_MODULE)
    lifecycle.run_and_assert_ok(
        env,
        "pm-set-anchor",
        "setup",
        "-n",
        str(anchor_dir),
        str(base_port),
        str(base_port + 1),
        str(base_port + 2),
    )

    lifecycle.run_and_assert_ok(env, "pm-set-target", "create", PROCESS_SERVER_MODULE)
    lifecycle.run_and_assert_ok(
        env,
        "pm-set-target",
        "setup",
        "-n",
        str(target_dir),
        str(target_port),
        str(target_port + 1),
        str(target_port + 2),
    )

    rejected = lifecycle.run_alphagsm(env, "pm-set-target", "set", "port", str(base_port))
    lifecycle.log_command_result("alphagsm pm-set-target set port", rejected)
    assert rejected.returncode != 0
    assert "Recommended free port set" in (rejected.stdout + rejected.stderr)

    target_data = lifecycle.load_server_data(home_dir, "pm-set-target")
    assert target_data["port"] == target_port

    try:
        lifecycle.run_and_assert_ok(env, "pm-set-target", "start")
        lifecycle.wait_for_tcp_open("127.0.0.1", target_port, START_TIMEOUT)
        _assert_query_and_info(lifecycle, env, "pm-set-target", target_port)
    finally:
        lifecycle.run_alphagsm(env, "pm-set-target", "stop", timeout=120)
        lifecycle.wait_for_closed("127.0.0.1", target_port, STOP_TIMEOUT)


@pytest.mark.parametrize(
    ("runtime_backend", "runtime_args"),
    (
        ("process", {}),
        ("docker", {"image": DOCKER_TEST_IMAGE}),
    ),
    ids=("process", "docker"),
)
def test_port_manager_start_preflight_blocks_taken_port_then_lifecycle_recovers(
    tmp_path,
    lifecycle,
    runtime_backend,
    runtime_args,
):
    """Start should fail while the port is live-occupied, then succeed after release."""

    lifecycle.require_backend_opt_in()
    if runtime_backend == "docker":
        lifecycle.require_command("docker")
        lifecycle.ensure_docker_image(DOCKER_TEST_IMAGE)

    home_dir = tmp_path / ("alphagsm-home-" + runtime_backend)
    home_dir.mkdir()
    config_path = tmp_path / ("alphagsm-" + runtime_backend + ".conf")
    install_dir = tmp_path / ("server-" + runtime_backend)

    port = lifecycle.pick_free_tcp_port()
    lifecycle.write_config(
        config_path,
        home_dir,
        "BkPort#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )
    env = lifecycle.alphagsm_env(config_path)

    server_name = "pm-preflight-" + runtime_backend
    lifecycle.run_and_assert_ok(env, server_name, "create", PROCESS_SERVER_MODULE)
    for key, value in runtime_args.items():
        lifecycle.run_and_assert_ok(env, server_name, "set", key, value)
    lifecycle.run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(install_dir),
        str(port),
        str(port + 1),
        str(port + 2),
    )

    blocker = lifecycle.bind_tcp_listener("127.0.0.1", port)
    try:
        blocked = lifecycle.run_alphagsm(env, server_name, "start")
        lifecycle.log_command_result("alphagsm " + server_name + " start", blocked)
        assert blocked.returncode != 0
        assert "claimed ports are not free" in (blocked.stdout + blocked.stderr)
    finally:
        blocker.close()

    try:
        lifecycle.run_and_assert_ok(env, server_name, "start")
        lifecycle.wait_for_tcp_open("127.0.0.1", port, START_TIMEOUT)
        _assert_query_and_info(lifecycle, env, server_name, port)
    finally:
        lifecycle.run_alphagsm(env, server_name, "stop", timeout=120)
        if runtime_backend == "docker":
            subprocess.run(
                ["docker", "rm", "-f", "alphagsm-" + server_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=60,
            )
        lifecycle.wait_for_closed("127.0.0.1", port, STOP_TIMEOUT)
