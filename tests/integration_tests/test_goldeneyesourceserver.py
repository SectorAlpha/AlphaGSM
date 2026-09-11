"""Integration test for goldeneyesourceserver.

ENABLED (BYO): stage a complete Source 2007 plus GoldenEye: Source server tree.
"""

import os
import shutil
import sys

import pytest

from conftest import (
    assert_alphagsm_result_ok,
    capture_alphagsm_stop,
    require_integration_opt_in,
    default_runtime_backend,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
STAGED_TREE_ENV = "ALPHAGSM_GOLDENEYE_SOURCE_SERVER_DIR"


def _stage_explicit_tree(staged_tree, install_dir):
    if not os.path.isdir(staged_tree):
        pytest.fail(
            "Explicit GoldenEye staged-tree input is not a readable directory",
            pytrace=False,
        )
    try:
        shutil.copytree(staged_tree, install_dir, symlinks=True)
    except OSError:
        pytest.fail(
            "Unable to copy the explicit GoldenEye staged-tree input",
            pytrace=False,
        )


def _run_asserted_lifecycle_command(env, server_name, *args):
    result = run_alphagsm(env, server_name, *args)
    log_command_result("alphagsm", result, command_args=(server_name,) + args)
    return assert_alphagsm_result_ok(result)


def _assert_query_semantics(output):
    if "Server is responding" not in output:
        raise AssertionError("GoldenEye query did not report a responding server")


def _assert_info_semantics(output):
    if "Players     : 0/" not in output:
        raise AssertionError("GoldenEye info did not report an empty server")


def _assert_info_json_semantics(payload):
    if payload.get("protocol") != "a2s":
        raise AssertionError("GoldenEye info JSON reported an unexpected protocol")
    if payload.get("players") != 0:
        raise AssertionError("GoldenEye info JSON reported an unexpected player count")


def test_goldeneyesourceserver_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "goldeneyesourceserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itgoldeneyesou"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    staged_tree = os.environ.get(STAGED_TREE_ENV, "").strip()
    if staged_tree:
        _stage_explicit_tree(staged_tree, install_dir)

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        result,
    )
    if result.returncode != 0 and not staged_tree:
        skip_for_known_steamcmd_issue(result)
    assert_alphagsm_result_ok(result)

    try:
        # start
        _run_asserted_lifecycle_command(env, server_name, "start")

        # wait for readiness
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        # status
        _run_asserted_lifecycle_command(env, server_name, "status")

        # query
        query_result = _run_asserted_lifecycle_command(env, server_name, "query")
        _assert_query_semantics(query_result.stdout)

        # info
        info_result = _run_asserted_lifecycle_command(env, server_name, "info")
        _assert_info_semantics(info_result.stdout)

        # info --json
        import json as _info_json
        info_json_result = _run_asserted_lifecycle_command(
            env, server_name, "info", "--json"
        )
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        _assert_info_json_semantics(_info_data)
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])

    # verify stopped
    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
