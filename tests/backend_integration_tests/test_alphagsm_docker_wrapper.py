"""Backend integration test for the root-level Docker wrapper."""

import json
import os
from pathlib import Path
import subprocess

import pytest
from tests.helpers import load_module_from_repo


pytestmark = pytest.mark.backend_integration

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "alphagsm-docker"
SERVER_NAME = "itdockerwrap"
SERVER_IMAGE = os.environ.get("ALPHAGSM_MANAGER_SERVER_IMAGE", "eclipse-temurin:25-jre")

runtime_module = load_module_from_repo(
    "backend_wrapper_runtime_module",
    "src/server/runtime.py",
)

WRAPPER_FAMILY_CASES = (
    ("java", "itwrap-java"),
    ("quake-linux", "itwrap-quake"),
    ("service-console", "itwrap-service"),
    ("simple-tcp", "itwrap-simple"),
    ("steamcmd-linux", "itwrap-steamcmd"),
    ("wine-proton", "itwrap-wine"),
)


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


def _parse_wrapper_json(stdout):
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError("No JSON payload found in wrapper output: %r" % (stdout,))


def _wrapper_family_image(runtime_family):
    override_key = "ALPHAGSM_WRAPPER_DOCKER_IMAGE_" + runtime_family.upper().replace("-", "_")
    if os.environ.get(override_key):
        return os.environ[override_key], True

    generic_key = "ALPHAGSM_BACKEND_DOCKER_IMAGE_" + runtime_family.upper().replace("-", "_")
    if os.environ.get(generic_key):
        return os.environ[generic_key], True

    sanitized = runtime_family.replace("-", "_")
    return ("alphagsm-wrapper-%s:test" % (sanitized,), False)


def _ensure_wrapper_family_image(lifecycle, runtime_family, image, pull_only):
    if pull_only:
        try:
            lifecycle.ensure_docker_image(image)
        except pytest.fail.Exception:
            pytest.skip(
                "Published runtime image is not available yet for %s: %s"
                % (runtime_family, image)
            )
        return

    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    if inspect.returncode == 0:
        return

    dockerfile = runtime_module.RUNTIME_FAMILY_DOCKERFILES[runtime_family]
    result = subprocess.run(
        ["docker", "build", "-f", str(REPO_ROOT / dockerfile), "-t", image, str(REPO_ROOT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=3600,
        check=False,
    )
    lifecycle.log_command_result("docker build " + image, result)
    assert result.returncode == 0, result.stderr or result.stdout


def _write_wrapper_probe_config(state_dir, lifecycle):
    home_dir = state_dir / "home"
    state_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    lifecycle.write_config(
        state_dir / "alphagsm.conf",
        home_dir,
        "BkWrap#",
        backend="subprocess",
        runtime_backend="docker",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )


def _assert_wrapper_query_and_info(lifecycle, env, server_name, port):
    query_result = _run_wrapper(lifecycle, env, server_name, "query", timeout=300)
    assert query_result.returncode == 0, query_result.stderr or query_result.stdout
    assert "Server port is open" in query_result.stdout, query_result.stdout

    info_result = _run_wrapper(lifecycle, env, server_name, "info", timeout=300)
    assert info_result.returncode == 0, info_result.stderr or info_result.stdout
    assert "Server port is open" in info_result.stdout, info_result.stdout

    info_json_result = _run_wrapper(
        lifecycle,
        env,
        server_name,
        "info",
        "--json",
        timeout=300,
    )
    assert info_json_result.returncode == 0, info_json_result.stderr or info_json_result.stdout
    info_data = _parse_wrapper_json(info_json_result.stdout)
    assert info_data["protocol"] == "tcp", info_data
    assert info_data["port"] == port, info_data


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


def test_root_wrapper_runs_docker_minecraft_info_lifecycle(tmp_path, lifecycle):
    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    docker_socket = Path("/var/run/docker.sock")
    if not docker_socket.exists():
        pytest.skip("Docker socket is required for the docker-wrapper integration test")
    if not _compose_available():
        pytest.skip("Docker Compose is required for the docker-wrapper integration test")

    state_dir = (tmp_path / "manager-home").resolve()
    container_name = "alphagsm-manager-wrap-" + str(lifecycle.pick_free_tcp_port())
    install_dir = state_dir / "servers" / SERVER_NAME
    port = lifecycle.pick_free_tcp_port()
    release_id, server_url = lifecycle.latest_minecraft_release()

    env = os.environ.copy()
    env["ALPHAGSM_HOME"] = str(state_dir)
    env["ALPHAGSM_MANAGER_CONTAINER_NAME"] = container_name
    env["ALPHAGSM_PULL_RUNTIME_IMAGES"] = "0"
    env["ALPHAGSM_MANAGER_SERVER_IMAGE"] = SERVER_IMAGE

    up_result = _run_wrapper(lifecycle, env, "up", "--develop", timeout=1800)
    assert up_result.returncode == 0, up_result.stderr or up_result.stdout

    try:
        lifecycle.ensure_docker_image(SERVER_IMAGE)

        create_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "create",
            "minecraft.vanilla",
            timeout=300,
        )
        assert create_result.returncode == 0, create_result.stderr or create_result.stdout

        set_image_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "set",
            "image",
            SERVER_IMAGE,
            timeout=300,
        )
        assert set_image_result.returncode == 0, set_image_result.stderr or set_image_result.stdout

        set_java_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "set",
            "java_major",
            "25",
            timeout=300,
        )
        assert set_java_result.returncode == 0, set_java_result.stderr or set_java_result.stdout

        setup_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "setup",
            "-n",
            "-l",
            str(port),
            str(install_dir),
            "-u",
            server_url,
            timeout=1200,
        )
        assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

        start_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "start",
            timeout=1200,
        )
        assert start_result.returncode == 0, start_result.stderr or start_result.stdout

        lifecycle.wait_for_status("127.0.0.1", port, 180)

        status_result = _run_wrapper(lifecycle, env, SERVER_NAME, "status", timeout=300)
        assert status_result.returncode == 0, status_result.stderr or status_result.stdout
        assert "Server is running" in status_result.stdout, status_result.stdout
        assert "Host connection details:" in status_result.stdout, status_result.stdout

        info_result = _run_wrapper(lifecycle, env, SERVER_NAME, "info", timeout=300)
        assert info_result.returncode == 0, info_result.stderr or info_result.stdout
        assert "Server info (SLP" in info_result.stdout, info_result.stdout

        info_json_result = _run_wrapper(
            lifecycle,
            env,
            SERVER_NAME,
            "info",
            "--json",
            timeout=300,
        )
        assert info_json_result.returncode == 0, info_json_result.stderr or info_json_result.stdout
        info_data = _parse_wrapper_json(info_json_result.stdout)
        assert info_data["protocol"] == "slp", info_data
        assert info_data.get("players_online", 0) == 0, info_data

        stop_result = _run_wrapper(lifecycle, env, SERVER_NAME, "stop", timeout=300)
        assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
        lifecycle.wait_for_closed("127.0.0.1", port, 90)
    finally:
        _run_wrapper(lifecycle, env, SERVER_NAME, "stop", timeout=300)
        _run_wrapper(lifecycle, env, "down", timeout=300)
        subprocess.run(
            ["docker", "rm", "-f", container_name, "alphagsm-" + SERVER_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )


@pytest.mark.parametrize(
    ("runtime_family", "server_name"),
    WRAPPER_FAMILY_CASES,
    ids=lambda case: case[0] if isinstance(case, tuple) else str(case),
)
def test_root_wrapper_probe_matrix_covers_all_docker_runtime_families(
    tmp_path,
    lifecycle,
    runtime_family,
    server_name,
):
    lifecycle.require_backend_opt_in()
    lifecycle.require_command("docker")

    docker_socket = Path("/var/run/docker.sock")
    if not docker_socket.exists():
        pytest.skip("Docker socket is required for the docker-wrapper integration test")
    if not _compose_available():
        pytest.skip("Docker Compose is required for the docker-wrapper integration test")

    state_dir = (tmp_path / ("manager-home-" + runtime_family)).resolve()
    container_name = "alphagsm-manager-wrap-" + runtime_family + "-" + str(lifecycle.pick_free_tcp_port())
    install_dir = state_dir / "servers" / server_name
    port = lifecycle.pick_free_tcp_port()
    image, pull_only = _wrapper_family_image(runtime_family)

    _write_wrapper_probe_config(state_dir, lifecycle)

    env = os.environ.copy()
    env["ALPHAGSM_HOME"] = str(state_dir)
    env["ALPHAGSM_MANAGER_CONTAINER_NAME"] = container_name
    env["ALPHAGSM_PULL_RUNTIME_IMAGES"] = "0"

    up_result = _run_wrapper(lifecycle, env, "up", "--develop", timeout=1800)
    assert up_result.returncode == 0, up_result.stderr or up_result.stdout

    try:
        _ensure_wrapper_family_image(lifecycle, runtime_family, image, pull_only)

        create_result = _run_wrapper(
            lifecycle,
            env,
            server_name,
            "create",
            "portprobe",
            timeout=300,
        )
        assert create_result.returncode == 0, create_result.stderr or create_result.stdout

        set_family_result = _run_wrapper(
            lifecycle,
            env,
            server_name,
            "set",
            "runtime_family",
            runtime_family,
            timeout=300,
        )
        assert set_family_result.returncode == 0, set_family_result.stderr or set_family_result.stdout

        set_image_result = _run_wrapper(
            lifecycle,
            env,
            server_name,
            "set",
            "image",
            image,
            timeout=300,
        )
        assert set_image_result.returncode == 0, set_image_result.stderr or set_image_result.stdout

        if runtime_family == "java":
            set_java_result = _run_wrapper(
                lifecycle,
                env,
                server_name,
                "set",
                "java_major",
                "25",
                timeout=300,
            )
            assert set_java_result.returncode == 0, set_java_result.stderr or set_java_result.stdout

        setup_result = _run_wrapper(
            lifecycle,
            env,
            server_name,
            "setup",
            "-n",
            str(install_dir),
            str(port),
            str(port + 1),
            str(port + 2),
            timeout=600,
        )
        assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

        start_result = _run_wrapper(lifecycle, env, server_name, "start", timeout=1200)
        assert start_result.returncode == 0, start_result.stderr or start_result.stdout

        lifecycle.wait_for_tcp_open("127.0.0.1", port, 180)

        status_result = _run_wrapper(lifecycle, env, server_name, "status", timeout=300)
        assert status_result.returncode == 0, status_result.stderr or status_result.stdout
        assert "Server is running" in status_result.stdout, status_result.stdout
        assert "Host connection details:" in status_result.stdout, status_result.stdout

        _assert_wrapper_query_and_info(lifecycle, env, server_name, port)

        stop_result = _run_wrapper(lifecycle, env, server_name, "stop", timeout=300)
        assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
        lifecycle.wait_for_closed("127.0.0.1", port, 90)

        final_status = _run_wrapper(lifecycle, env, server_name, "status", timeout=300)
        assert final_status.returncode == 0, final_status.stderr or final_status.stdout
        assert "isn't running" in final_status.stdout, final_status.stdout
    finally:
        _run_wrapper(lifecycle, env, server_name, "stop", timeout=300)
        _run_wrapper(lifecycle, env, "down", timeout=300)
        subprocess.run(
            ["docker", "rm", "-f", container_name, "alphagsm-" + server_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )