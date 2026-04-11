"""Active Docker runtime lifecycle tests driven by the backend family matrix."""

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


def _docker_image_for_case(case):
    """Resolve the Docker image to use for an active lifecycle case."""

    family_env = "ALPHAGSM_BACKEND_DOCKER_IMAGE_" + case.runtime_family.upper().replace("-", "_")
    image = os.environ.get(family_env) or os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE")
    if image:
        return image
    return case.default_image


def _run_setup_for_case(lifecycle, env, case, install_dir, port):
    """Run the module-specific setup command for an active lifecycle case."""

    if case.setup_profile == "minecraft-vanilla-latest":
        _release_id, server_url = lifecycle.latest_minecraft_release()
        lifecycle.run_and_assert_ok(
            env,
            case.server_name,
            "setup",
            "-n",
            "-l",
            str(port),
            str(install_dir),
            "-u",
            server_url,
        )
        return

    if case.setup_profile == "minecraft-java-listen-port":
        lifecycle.run_and_assert_ok(
            env,
            case.server_name,
            "setup",
            "-n",
            "-l",
            str(port),
            str(install_dir),
        )
        return

    if case.setup_profile == "minecraft-java-proxy-port":
        lifecycle.run_and_assert_ok(
            env,
            case.server_name,
            "setup",
            "-n",
            str(port),
            str(install_dir),
        )
        return

    raise AssertionError("Unsupported active Docker setup profile: %s" % (case.setup_profile,))


def _assert_case_query_and_info(lifecycle, env, case):
    """Assert AlphaGSM query/info behaviour for an active Docker lifecycle case."""

    query_result = lifecycle.run_and_assert_ok(env, case.server_name, "query")
    assert case.query_marker in query_result.stdout, (
        "Unexpected query output for %s: %r" % (case.slug, query_result.stdout)
    )

    info_result = lifecycle.run_and_assert_ok(env, case.server_name, "info")
    assert case.info_marker in info_result.stdout, (
        "Unexpected info output for %s: %r" % (case.slug, info_result.stdout)
    )

    info_json_result = lifecycle.run_and_assert_ok(env, case.server_name, "info", "--json")
    info_data = json.loads(info_json_result.stdout.strip())
    assert info_data["protocol"] == case.info_protocol, (
        "Unexpected info protocol for %s: %r" % (case.slug, info_data)
    )
    assert info_data.get("players_online", 0) == 0, (
        "Expected 0 players_online on a fresh Docker lifecycle case: %r" % (info_data,)
    )


@pytest.mark.parametrize("case", family_matrix.active_cases(), ids=lambda case: case.slug)
def test_active_docker_runtime_lifecycle_cases(tmp_path, lifecycle, case):
    """Run the full AlphaGSM Docker lifecycle for each active matrix case."""

    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / case.slug
    config_path = tmp_path / ("alphagsm-%s.conf" % (case.slug,))

    home_dir.mkdir()

    port = lifecycle.pick_free_tcp_port()
    image = _docker_image_for_case(case)
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
    lifecycle.run_and_assert_ok(env, case.server_name, "set", "java_major", "25")

    container_name = "alphagsm-" + case.server_name
    try:
        _run_setup_for_case(lifecycle, env, case, install_dir, port)
        lifecycle.run_and_assert_ok(env, case.server_name, "start")
        lifecycle.wait_for_status("127.0.0.1", port, 180)

        status_result = lifecycle.run_and_assert_ok(env, case.server_name, "status")
        assert "Server is running" in status_result.stdout, (
            "Expected running status for %s: %r" % (case.slug, status_result.stdout)
        )

        _assert_case_query_and_info(lifecycle, env, case)

        lifecycle.run_and_assert_ok(env, case.server_name, "stop")
        lifecycle.wait_for_closed("127.0.0.1", port, 90)

        final_status = lifecycle.run_and_assert_ok(env, case.server_name, "status")
        assert "isn't running" in final_status.stdout, (
            "Expected stopped status for %s: %r" % (case.slug, final_status.stdout)
        )
    finally:
        lifecycle.run_alphagsm(env, case.server_name, "stop", timeout=120)
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=60,
        )
