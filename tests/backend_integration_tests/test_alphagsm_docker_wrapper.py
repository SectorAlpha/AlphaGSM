"""Backend integration test for the root-level Docker wrapper."""

import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.backend_integration

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "alphagsm-docker"
SERVER_NAME = "itdockerwrap"


def _run_wrapper(lifecycle, env, *args, timeout=1200):
    result = subprocess.run(
        [str(WRAPPER), *args],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    lifecycle.log_command_result("./alphagsm-docker " + " ".join(args), result)
    return result


def _compose_available():
    plugin = subprocess.run(
        ["docker", "compose", "version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    if plugin.returncode == 0:
        return True
    standalone = subprocess.run(
        ["docker-compose", "version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    return standalone.returncode == 0


def test_root_wrapper_starts_manager_and_forwards_commands(tmp_path, lifecycle):
    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    docker_socket = Path("/var/run/docker.sock")
    if not docker_socket.exists():
        pytest.skip("Docker socket is required for the docker-wrapper integration test")
    if not _compose_available():
        pytest.skip("Docker Compose is required for the docker-wrapper integration test")

    state_dir = (tmp_path / "manager-home").resolve()
    container_name = "alphagsm-manager-wrap-" + str(lifecycle.pick_free_tcp_port())
    server_data = state_dir / "home" / "conf" / f"{SERVER_NAME}.json"

    env = os.environ.copy()
    env["ALPHAGSM_HOME"] = str(state_dir)
    env["ALPHAGSM_MANAGER_CONTAINER_NAME"] = container_name
    env["ALPHAGSM_PULL_RUNTIME_IMAGES"] = "0"

    up_result = _run_wrapper(lifecycle, env, "up", timeout=1800)
    assert up_result.returncode == 0, up_result.stderr or up_result.stdout
    assert (state_dir / "alphagsm.conf").exists()

    try:
        create_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "create",
            "minecraft.vanilla",
            timeout=300,
        )
        assert create_result.returncode == 0, create_result.stderr or create_result.stdout
        assert server_data.exists()

        set_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "set",
            "image",
            "eclipse-temurin:25-jre",
            timeout=300,
        )
        assert set_result.returncode == 0, set_result.stderr or set_result.stdout
        assert "eclipse-temurin:25-jre" in server_data.read_text(encoding="utf-8")
    finally:
        _run_wrapper(lifecycle, env, "down", timeout=300)
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )