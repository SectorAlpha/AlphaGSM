"""Manager-container lifecycle test for Docker-backed Minecraft."""

import json
import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.backend_integration

REPO_ROOT = Path(__file__).resolve().parents[2]
MANAGER_DOCKERFILE = REPO_ROOT / "docker" / "manager" / "Dockerfile"
MANAGER_IMAGE = os.environ.get("ALPHAGSM_MANAGER_TEST_IMAGE", "alphagsm:test")
SERVER_IMAGE = os.environ.get("ALPHAGSM_MANAGER_SERVER_IMAGE", "eclipse-temurin:25-jre")
SERVER_NAME = "bkmgr-vanilla"
START_TIMEOUT = 180
STOP_TIMEOUT = 90


def _run_command(lifecycle, label, command, timeout):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    lifecycle.log_command_result(label, result)
    return result


def _ensure_manager_image(lifecycle):
    build = _run_command(
        lifecycle,
        "docker build manager image",
        [
            "docker",
            "build",
            "-f",
            str(MANAGER_DOCKERFILE),
            "-t",
            MANAGER_IMAGE,
            str(REPO_ROOT),
        ],
        timeout=1800,
    )
    assert build.returncode == 0, build.stderr or build.stdout


def _run_manager_alphagsm(lifecycle, container_name, *args, timeout=1200):
    result = _run_command(
        lifecycle,
        "docker exec " + container_name + " python alphagsm " + " ".join(args),
        ["docker", "exec", container_name, "python", "alphagsm", *args],
        timeout=timeout,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def test_manager_container_launches_docker_minecraft(tmp_path, lifecycle):
    """Run AlphaGSM inside Docker and prove it launches Minecraft in Docker."""

    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    docker_socket = Path("/var/run/docker.sock")
    if not docker_socket.exists():
        pytest.skip("Docker socket is required for the manager-container lifecycle test")

    shared_root = tmp_path.resolve()
    home_dir = shared_root / "alphagsm-home"
    install_dir = shared_root / "servers" / "minecraft-vanilla"
    config_path = shared_root / "alphagsm-manager.conf"

    home_dir.mkdir()
    install_dir.parent.mkdir(parents=True, exist_ok=True)

    port = lifecycle.pick_free_tcp_port()
    release_id, server_url = lifecycle.latest_minecraft_release()
    container_name = "alphagsm-manager-it-" + str(port)
    minecraft_container_name = "alphagsm-" + SERVER_NAME

    _ensure_manager_image(lifecycle)

    lifecycle.write_config(
        config_path,
        home_dir,
        "BkMgr#",
        backend="subprocess",
        runtime_backend="docker",
    )

    run_result = _run_command(
        lifecycle,
        "docker run manager container",
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--workdir",
            "/opt/alphagsm",
            "-e",
            "ALPHAGSM_CONFIG_LOCATION=" + str(config_path),
            "-e",
            "ALPHAGSM_PULL_RUNTIME_IMAGES=0",
            "-e",
            "PYTHONPATH=/opt/alphagsm/src",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            str(shared_root) + ":" + str(shared_root),
            MANAGER_IMAGE,
        ],
        timeout=180,
    )
    assert run_result.returncode == 0, run_result.stderr or run_result.stdout

    try:
        print(f"Minecraft {release_id}, port {port}, backend=manager-container")

        _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "create", "minecraft.vanilla")
        _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "set", "image", SERVER_IMAGE)
        _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "set", "java_major", "25")
        _run_manager_alphagsm(
            lifecycle,
            container_name,
            SERVER_NAME,
            "setup",
            "-n",
            "-l",
            str(port),
            str(install_dir),
            "-u",
            server_url,
        )

        assert (install_dir / "minecraft_server.jar").exists()
        assert (install_dir / "eula.txt").exists()
        assert (install_dir / "server.properties").exists()

        _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "start")
        lifecycle.wait_for_status("127.0.0.1", port, START_TIMEOUT)

        inspect_result = _run_command(
            lifecycle,
            "docker inspect child minecraft container",
            [
                "docker",
                "inspect",
                minecraft_container_name,
                "--format",
                "{{json .State}}\n{{.Config.Image}}",
            ],
            timeout=60,
        )
        assert inspect_result.returncode == 0, inspect_result.stderr or inspect_result.stdout
        inspect_lines = inspect_result.stdout.strip().splitlines()
        state = json.loads(inspect_lines[0])
        assert state["Running"] is True, inspect_result.stdout
        assert inspect_lines[1].strip() == SERVER_IMAGE, inspect_result.stdout

        status_result = _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "status")
        assert "Server is running" in status_result.stdout, status_result.stdout

        query_result = _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "query")
        assert "Server port is open" in query_result.stdout, query_result.stdout

        info_result = _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "info")
        assert "Server info (SLP" in info_result.stdout, info_result.stdout

        info_json_result = _run_manager_alphagsm(
            lifecycle,
            container_name,
            SERVER_NAME,
            "info",
            "--json",
        )
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "slp", info_data
        assert info_data.get("players_online", 0) == 0, info_data

        _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "stop")
        lifecycle.wait_for_closed("127.0.0.1", port, STOP_TIMEOUT)

        final_status = _run_manager_alphagsm(lifecycle, container_name, SERVER_NAME, "status")
        assert "isn't running" in final_status.stdout, final_status.stdout
    finally:
        _run_command(
            lifecycle,
            "best-effort manager stop",
            ["docker", "exec", container_name, "python", "alphagsm", SERVER_NAME, "stop"],
            timeout=120,
        )
        _run_command(
            lifecycle,
            "remove child minecraft container",
            ["docker", "rm", "-f", minecraft_container_name],
            timeout=60,
        )
        _run_command(
            lifecycle,
            "remove manager container",
            ["docker", "rm", "-f", container_name],
            timeout=60,
        )