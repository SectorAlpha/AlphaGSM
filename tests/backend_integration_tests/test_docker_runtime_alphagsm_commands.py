"""Integration test: exercise AlphaGSM CLI commands against Docker runtime.

This test reuses the same lifecycle family matrix as the active Docker
lifecycle tests but focuses on running a broader set of AlphaGSM commands
against a started container to validate the CLI/runtime integration.

Note: These tests are intended for CI or a machine configured to run
backend integration tests. Do not run them locally unless you opt-in via
`ALPHAGSM_RUN_BACKEND_INTEGRATION=1`.
"""

import json
import os
import subprocess

import pytest
from tests.helpers import load_module_from_repo


pytestmark = pytest.mark.backend_integration


family_matrix = load_module_from_repo(
    "backend_docker_family_matrix_runtime",
    "tests/backend_integration_tests/docker_family_matrix.py",
)


@pytest.mark.parametrize("case", family_matrix.active_cases(), ids=lambda case: case.slug)
def test_alphagsm_commands_inside_docker(tmp_path, lifecycle, case):
    """Create a server, start it in Docker, then run common AlphaGSM commands.

    This mirrors a realistic workflow and fails fast on unexpected CLI/runtime
    integration issues.
    """

    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / case.slug
    config_path = tmp_path / ("alphagsm-%s.conf" % (case.slug,))

    home_dir.mkdir()

    port = lifecycle.pick_free_tcp_port()
    image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE") or case.default_image
    assert image, "No Docker image configured for active Docker case %s" % (case.slug,)
    lifecycle.ensure_docker_image(image)

    lifecycle.write_config(
        config_path,
        home_dir,
        "BkDocker#",
        backend="subprocess",
        runtime_backend="docker",
    )
    env = lifecycle.alphagsm_env(config_path)

    lifecycle.run_and_assert_ok(env, case.server_name, "create", case.module_name)
    lifecycle.run_and_assert_ok(env, case.server_name, "set", "image", image)

    try:
        # Module-specific setup
        if case.setup_profile:
            lifecycle.run_and_assert_ok(env, case.server_name, "setup", "-n", str(port), str(install_dir))

        lifecycle.run_and_assert_ok(env, case.server_name, "start")

        # wait for basic readiness (reuse existing validators)
        if case.validator == "minecraft-status":
            lifecycle.wait_for_status("127.0.0.1", port, 180)
        elif case.validator == "tcp-open":
            lifecycle.wait_for_tcp_open("127.0.0.1", port, 180)

        # Run a series of AlphaGSM commands against the running container
        cmds = [
            ("status", []),
            ("info", []),
            ("info", ["--json"]),
            ("query", []),
        ]

        for cmd, args in cmds:
            result = lifecycle.run_alphagsm(env, case.server_name, cmd, *args)
            lifecycle.log_command_result("alphagsm %s %s" % (cmd, " ".join(args)), result)
            assert result.returncode == 0, (cmd, result.stderr or result.stdout)
            if cmd == "info" and args == ["--json"]:
                # validate JSON output
                data = json.loads(result.stdout.strip())
                assert "protocol" in data

        # stop and verify shutdown
        lifecycle.run_and_assert_ok(env, case.server_name, "stop")
        lifecycle.wait_for_closed("127.0.0.1", port, 90)

    finally:
        # best-effort cleanup
        subprocess.run(["docker", "rm", "-f", "alphagsm-" + case.server_name], check=False)
        lifecycle.run_alphagsm(env, case.server_name, "stop", timeout=120)
