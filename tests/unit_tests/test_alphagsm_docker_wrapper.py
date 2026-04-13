"""Unit tests for the root-level Docker wrapper."""

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "alphagsm-docker"


def _write_server_config(state_dir, server_name, payload):
    conf_dir = state_dir / "home" / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / f"{server_name}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_fake_docker(bin_dir):
    fake_docker = bin_dir / "docker"
    fake_docker.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "log_path = Path(os.environ['FAKE_DOCKER_LOG'])",
                "state_path = Path(os.environ['FAKE_DOCKER_STATE'])",
                "image_path = Path(os.environ['FAKE_DOCKER_IMAGE_STATE'])",
                "containers_json = os.environ.get('FAKE_DOCKER_CONTAINERS_JSON', '{}')",
                "try:",
                "    containers = json.loads(containers_json) if containers_json else {}",
                "except json.JSONDecodeError:",
                "    containers = {}",
                "entry = {'argv': sys.argv[1:], 'alphagsm_home': os.environ.get('ALPHAGSM_HOME', ''), 'pull_runtime_images': os.environ.get('ALPHAGSM_PULL_RUNTIME_IMAGES', ''), 'manager_image': os.environ.get('ALPHAGSM_MANAGER_IMAGE', '')}",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(entry) + '\\n')",
                "args = sys.argv[1:]",
                "state = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''",
                "image_state = image_path.read_text(encoding='utf-8').strip() if image_path.exists() else ''",
                "container_name = None",
                "if args[:1] in (['inspect'], ['port']) and args[1:2] and not args[1].startswith('-'):",
                "    container_name = args[1]",
                "elif args[:1] == ['attach'] and args[1:2]:",
                "    container_name = args[1]",
                "container = containers.get(container_name, {}) if container_name else {}",
                "if args[:2] == ['compose', 'version']:",
                "    sys.exit(0 if os.environ.get('FAKE_DOCKER_COMPOSE_AVAILABLE', '1') == '1' else 1)",
                "if args[:2] == ['image', 'inspect']:",
                "    image = args[-1]",
                "    sys.exit(0 if image_state == image else 1)",
                "if args[:1] == ['pull']:",
                "    image = args[-1]",
                "    if os.environ.get('FAKE_DOCKER_PULL_FAIL', '0') == '1':",
                "        sys.exit(1)",
                "    image_path.write_text(image, encoding='utf-8')",
                "    sys.exit(0)",
                "if args[:1] == ['port']:",
                "    if state != 'running':",
                "        sys.exit(1)",
                "    mapping = os.environ.get('FAKE_DOCKER_PORT_OUTPUT', '')",
                "    if mapping:",
                "        sys.stdout.write(mapping)",
                "        if not mapping.endswith('\\n'):",
                "            sys.stdout.write('\\n')",
                "    sys.exit(0)",
                "if args[:1] == ['inspect']:",
                "    if container_name and container:",
                "        if '-f' in args:",
                "            fmt = args[args.index('-f') + 1] if args.index('-f') + 1 < len(args) else ''",
                "            if fmt == '{{.State.Running}}':",
                "                sys.stdout.write('true\\n' if container.get('state') == 'running' else 'false\\n')",
                "            else:",
                "                sys.stdout.write('{}\\n')",
                "        else:",
                "            sys.stdout.write(json.dumps(container) + '\\n')",
                "        sys.exit(0)",
                "    if state == '':",
                "        sys.exit(1)",
                "    if '-f' in args:",
                "        sys.stdout.write('true\\n' if state == 'running' else 'false\\n')",
                "    else:",
                "        sys.stdout.write('{}\\n')",
                "    sys.exit(0)",
                "if args[:1] == ['attach']:",
                "    if container_name and container:",
                "        sys.stdout.write('ATTACHED:' + container_name + '\\n')",
                "        sys.exit(0)",
                "    sys.stderr.write('Unhandled attach target: ' + ' '.join(args) + '\\n')",
                "    sys.exit(1)",
                "if 'up' in args:",
                "    state_path.write_text('running', encoding='utf-8')",
                "    image = os.environ.get('ALPHAGSM_MANAGER_IMAGE', '')",
                "    if image:",
                "        image_path.write_text(image, encoding='utf-8')",
                "    sys.exit(0)",
                "if 'down' in args:",
                "    state_path.unlink(missing_ok=True)",
                "    sys.exit(0)",
                "if 'config' in args:",
                "    sys.stdout.write('services:\\n  alphagsm: {}\\n')",
                "    sys.exit(0)",
                "if 'exec' in args:",
                "    exec_index = args.index('exec')",
                "    forwarded = args[exec_index + 1:]",
                "    sys.stdout.write('FORWARDED:' + ' '.join(forwarded) + '\\n')",
                "    sys.exit(0)",
                "if 'logs' in args:",
                "    sys.exit(0)",
                "sys.stderr.write('Unhandled fake docker args: ' + ' '.join(args) + '\\n')",
                "sys.exit(1)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)


def _write_fake_docker_compose(bin_dir):
    fake_docker_compose = bin_dir / "docker-compose"
    fake_docker_compose.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "log_path = Path(os.environ['FAKE_DOCKER_LOG'])",
                "state_path = Path(os.environ['FAKE_DOCKER_STATE'])",
                "entry = {'argv': sys.argv[1:], 'tool': 'docker-compose', 'alphagsm_home': os.environ.get('ALPHAGSM_HOME', '')}",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(entry) + '\\n')",
                "args = sys.argv[1:]",
                "state = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''",
                "if args[:1] == ['version']:",
                "    sys.exit(0)",
                "if args[:1] == ['inspect']:",
                "    if state == '':",
                "        sys.exit(1)",
                "    if '-f' in args:",
                "        sys.stdout.write('true\\n' if state == 'running' else 'false\\n')",
                "    else:",
                "        sys.stdout.write('{}\\n')",
                "    sys.exit(0)",
                "if 'up' in args:",
                "    state_path.write_text('running', encoding='utf-8')",
                "    sys.exit(0)",
                "if 'down' in args:",
                "    state_path.unlink(missing_ok=True)",
                "    sys.exit(0)",
                "if 'config' in args:",
                "    sys.stdout.write('services:\\n  alphagsm: {}\\n')",
                "    sys.exit(0)",
                "if 'exec' in args:",
                "    exec_index = args.index('exec')",
                "    forwarded = args[exec_index + 1:]",
                "    sys.stdout.write('FORWARDED:' + ' '.join(forwarded) + '\\n')",
                "    sys.exit(0)",
                "if 'logs' in args:",
                "    sys.exit(0)",
                "sys.stderr.write('Unhandled fake docker-compose args: ' + ' '.join(args) + '\\n')",
                "sys.exit(1)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_docker_compose.chmod(0o755)


def _run_wrapper(
    tmp_path,
    *args,
    initial_state=None,
    docker_compose_available=True,
    install_standalone_compose=False,
    port_output=None,
    fake_containers=None,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log_path = tmp_path / "docker.log"
    state_path = tmp_path / "docker.state"
    image_state_path = tmp_path / "docker.image"
    state_dir = tmp_path / "state"
    _write_fake_docker(bin_dir)
    if install_standalone_compose:
        _write_fake_docker_compose(bin_dir)
    if initial_state is not None:
        state_path.write_text(initial_state, encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["FAKE_DOCKER_LOG"] = str(log_path)
    env["FAKE_DOCKER_STATE"] = str(state_path)
    env["FAKE_DOCKER_IMAGE_STATE"] = str(image_state_path)
    env["ALPHAGSM_HOME"] = str(state_dir)
    env["FAKE_DOCKER_COMPOSE_AVAILABLE"] = "1" if docker_compose_available else "0"
    if port_output is not None:
        env["FAKE_DOCKER_PORT_OUTPUT"] = port_output
    if fake_containers is not None:
        env["FAKE_DOCKER_CONTAINERS_JSON"] = json.dumps(fake_containers)

    result = subprocess.run(
        ["bash", str(WRAPPER), *args],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    log_entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return result, state_dir, log_entries


def test_wrapper_bootstraps_config_before_compose_command(tmp_path):
    result, state_dir, log_entries = _run_wrapper(tmp_path, "compose", "config")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    config_text = (state_dir / "alphagsm.conf").read_text(encoding="utf-8")
    assert f"alphagsm_path = {state_dir}/home" in config_text
    assert any(entry["argv"][:2] == ["compose", "version"] for entry in log_entries)
    assert any("config" in entry["argv"] for entry in log_entries)
    assert all(entry["pull_runtime_images"] == "0" for entry in log_entries)


def test_wrapper_start_and_stop_aliases_map_to_compose_up_and_down(tmp_path):
    start_result, state_dir, start_entries = _run_wrapper(tmp_path, "start")

    assert start_result.returncode == 0, start_result.stderr or start_result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    assert any(
        entry["manager_image"] == "ghcr.io/sectoralpha/alphagsm:latest"
        for entry in start_entries
        if "up" in entry["argv"]
    )
    assert any("up" in entry["argv"] for entry in start_entries)

    stop_result, _, stop_entries = _run_wrapper(tmp_path, "stop")

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    assert any("down" in entry["argv"] for entry in stop_entries)


def test_wrapper_start_develop_persists_local_build_mode(tmp_path):
    result, state_dir, log_entries = _run_wrapper(tmp_path, "start", "--develop")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / ".manager-mode").read_text(encoding="utf-8").strip() == "develop"
    assert any("up" in entry["argv"] and "--build" in entry["argv"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any(entry["manager_image"] == "alphagsm:dev" for entry in log_entries if "up" in entry["argv"])


def test_wrapper_starts_manager_and_forwards_alphagsm_command(tmp_path):
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "create",
        "minecraft.vanilla",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    assert any(entry["argv"][:1] == ["inspect"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("up" in entry["argv"] for entry in log_entries)
    assert not any("--build" in entry["argv"] for entry in log_entries if "up" in entry["argv"])
    assert any(
        entry["argv"][-6:] == [
            "exec",
            "alphagsm",
            "python",
            "alphagsm",
            "demo",
            "create",
            "minecraft.vanilla",
        ][-6:]
        and entry["alphagsm_home"] == str(state_dir)
        for entry in log_entries
    )
    assert "FORWARDED:-T alphagsm python alphagsm demo create minecraft.vanilla" in result.stdout


def test_wrapper_recreates_stopped_manager_without_rebuild(tmp_path):
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="stopped",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    assert any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("--force-recreate" in entry["argv"] for entry in log_entries if "up" in entry["argv"])
    assert not any("--build" in entry["argv"] for entry in log_entries if "up" in entry["argv"])
    assert "Running AlphaGSM command in manager container..." in result.stdout


def test_wrapper_status_appends_host_connection_details(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "scp",
        "status",
        initial_state="running",
        port_output="7777/tcp -> 0.0.0.0:7777\n7777/udp -> 0.0.0.0:7777\n7778/tcp -> 0.0.0.0:7778",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "FORWARDED:-T alphagsm python alphagsm scp status" in result.stdout
    assert "Host connection details:" in result.stdout
    assert "Host: 127.0.0.1 (or this machine's reachable IP)" in result.stdout
    assert "7777/tcp -> 0.0.0.0:7777" in result.stdout
    assert "7777/udp -> 0.0.0.0:7777" in result.stdout
    assert "7778/tcp -> 0.0.0.0:7778" in result.stdout
    assert "Connect from this host: 127.0.0.1:7777/tcp" in result.stdout
    assert "Connect from this host: 127.0.0.1:7777/udp" in result.stdout
    assert "Connect from this host: 127.0.0.1:7778/tcp" in result.stdout
    assert any(entry["argv"][:1] == ["port"] for entry in log_entries)


def test_wrapper_connect_attaches_to_explicit_container_name_without_manager_exec(tmp_path):
    fake_containers = {
        "custom-demo": {
            "state": "running",
            "ports": "25565/tcp -> 0.0.0.0:25565",
        }
    }
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "connect",
        fake_containers=fake_containers,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Detach with Ctrl-p Ctrl-q" in result.stdout
    assert "ATTACHED:custom-demo" in result.stdout
    assert any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)


def test_wrapper_connect_rejects_non_docker_server(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(state_dir, "demo", {"runtime": "process"})
    result, _, _ = _run_wrapper(tmp_path, "demo", "connect")

    assert result.returncode != 0
    assert "only attaches to Docker-backed servers" in result.stderr


def test_wrapper_start_appends_host_connection_details(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "mymc",
        "start",
        port_output="25566/tcp -> 0.0.0.0:25566\n25566/tcp -> :::25566",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "FORWARDED:-T alphagsm python alphagsm mymc start" in result.stdout
    assert "Host connection details:" in result.stdout
    assert "Connect from this host: 127.0.0.1:25566/tcp" in result.stdout
    assert result.stdout.count("Connect from this host: 127.0.0.1:25566/tcp") == 1
    assert any(entry["argv"][:1] == ["port"] for entry in log_entries)


def test_wrapper_builds_locally_when_remote_pull_fails(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_fake_docker(bin_dir)
    log_path = tmp_path / "docker.log"
    state_path = tmp_path / "docker.state"
    image_state_path = tmp_path / "docker.image"
    state_dir = tmp_path / "state"

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["FAKE_DOCKER_LOG"] = str(log_path)
    env["FAKE_DOCKER_STATE"] = str(state_path)
    env["FAKE_DOCKER_IMAGE_STATE"] = str(image_state_path)
    env["ALPHAGSM_HOME"] = str(state_dir)
    env["FAKE_DOCKER_COMPOSE_AVAILABLE"] = "1"
    env["FAKE_DOCKER_PULL_FAIL"] = "1"

    result = subprocess.run(
        ["bash", str(WRAPPER), "start"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    log_entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("--build" in entry["argv"] for entry in log_entries if "up" in entry["argv"])


def test_wrapper_falls_back_to_docker_compose_when_plugin_is_unavailable(tmp_path):
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "config",
        docker_compose_available=False,
        install_standalone_compose=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    assert any(entry.get("tool") == "docker-compose" for entry in log_entries)


def test_wrapper_prefers_docker_compose_plugin_when_both_are_available(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "config",
        docker_compose_available=True,
        install_standalone_compose=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(entry["argv"][:2] == ["compose", "version"] for entry in log_entries)
    assert not any(entry.get("tool") == "docker-compose" for entry in log_entries)
