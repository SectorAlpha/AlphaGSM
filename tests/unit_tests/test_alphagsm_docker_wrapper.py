"""Unit tests for the root-level Docker wrapper."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "alphagsm-docker"
HOST_UID = str(os.geteuid())
HOST_GID = str(os.getegid())


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
                "entry = {'argv': sys.argv[1:], 'alphagsm_home': os.environ.get('ALPHAGSM_HOME', ''), 'pull_runtime_images': os.environ.get('ALPHAGSM_PULL_RUNTIME_IMAGES', ''), 'manager_image': os.environ.get('ALPHAGSM_MANAGER_IMAGE', ''), 'host_uid': os.environ.get('ALPHAGSM_HOST_UID', ''), 'host_gid': os.environ.get('ALPHAGSM_HOST_GID', ''), 'docker_gid': os.environ.get('ALPHAGSM_DOCKER_GID', ''), 'docker_socket': os.environ.get('ALPHAGSM_DOCKER_SOCKET', '')}",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(entry) + '\\n')",
                "args = sys.argv[1:]",
                "state = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''",
                "image_state = image_path.read_text(encoding='utf-8').strip() if image_path.exists() else ''",
                "manager_identity = os.environ.get('FAKE_MANAGER_INSPECT_IDENTITY', '1234:2345|[\"3456\"]')",
                "manager_socket_source = os.environ.get('FAKE_MANAGER_INSPECT_SOCKET_SOURCE', '/var/run/docker.sock')",
                "container_name = None",
                "if args[:1] in (['inspect'], ['port'], ['attach'], ['logs']) and len(args) > 1:",
                "    container_name = args[-1]",
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
                "    if container_name and container:",
                "        mapping = container.get('ports', '')",
                "    else:",
                "        if state != 'running':",
                "            sys.exit(1)",
                "        mapping = os.environ.get('FAKE_DOCKER_PORT_OUTPUT', '')",
                "    if isinstance(mapping, list):",
                "        mapping = '\\n'.join(str(item) for item in mapping)",
                "    if mapping:",
                "        sys.stdout.write(str(mapping))",
                "        if not str(mapping).endswith('\\n'):",
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
                "        fmt = args[args.index('-f') + 1] if args.index('-f') + 1 < len(args) else ''",
                "        if fmt == '{{.State.Running}}':",
                "            sys.stdout.write('true\\n' if state == 'running' else 'false\\n')",
                "        elif fmt == '{{.Config.User}}|{{json .HostConfig.GroupAdd}}':",
                "            sys.stdout.write(manager_identity + '\\n')",
                "        elif fmt == '{{range .Mounts}}{{if eq .Destination \"/var/run/docker.sock\"}}{{println .Source}}{{end}}{{end}}':",
                "            if manager_socket_source:",
                "                sys.stdout.write(manager_socket_source + '\\n')",
                "        else:",
                "            sys.stdout.write('{}\\n')",
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
                "if args[:1] == ['logs']:",
                "    if container_name and container:",
                "        logs_output = container.get('logs', '')",
                "    else:",
                "        logs_output = os.environ.get('FAKE_DOCKER_LOGS_OUTPUT', '')",
                "    if logs_output:",
                "        sys.stdout.write(str(logs_output))",
                "        if not str(logs_output).endswith('\\n'):",
                "            sys.stdout.write('\\n')",
                "    sys.exit(0)",
                "sys.stderr.write('Unhandled fake docker args: ' + ' '.join(args) + '\\n')",
                "sys.exit(1)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_docker.write_text(
        fake_docker.read_text(encoding="utf-8").replace(
            "#!/usr/bin/env python3",
            f"#!{sys.executable}",
            1,
        ),
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)


def _write_fake_identity_tools(bin_dir):
    fake_id = bin_dir / "id"
    fake_id.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
    -u) printf '%s\n' "${FAKE_HOST_UID:-1234}" ;;
    -g) printf '%s\n' "${FAKE_HOST_GID:-2345}" ;;
    *) exit 2 ;;
esac
""",
        encoding="utf-8",
    )
    fake_id.chmod(0o755)

    fake_stat = bin_dir / "stat"
    fake_stat.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" && "${2:-}" == "%g" ]]; then
    printf '%s\n' "${FAKE_DOCKER_GID:-3456}"
    exit 0
fi
if [[ "${1:-}" == "-c" && "${2:-}" == "%u|%g|%a|%F" ]]; then
    path="${3:-}"
    if [[ -L "$path" ]]; then
        file_type="symbolic link"
    elif [[ -d "$path" ]]; then
        file_type="directory"
    elif [[ -f "$path" ]]; then
        file_type="regular file"
    else
        file_type="other"
    fi
    mode="$(/usr/bin/stat -c '%a' -- "$path")"
    printf '%s|%s|%s|%s\n' \
        "${FAKE_STATE_UID:-1234}" \
        "${FAKE_STATE_GID:-2345}" \
        "$mode" \
        "$file_type"
    exit 0
fi
if [[ "${1:-}" == "-f" && "${2:-}" == "%g" ]]; then
    printf '%s\n' "${FAKE_DOCKER_GID:-3456}"
    exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_stat.chmod(0o755)


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
                "entry = {'argv': sys.argv[1:], 'tool': 'docker-compose', 'alphagsm_home': os.environ.get('ALPHAGSM_HOME', ''), 'host_uid': os.environ.get('ALPHAGSM_HOST_UID', ''), 'host_gid': os.environ.get('ALPHAGSM_HOST_GID', ''), 'docker_gid': os.environ.get('ALPHAGSM_DOCKER_GID', ''), 'docker_socket': os.environ.get('ALPHAGSM_DOCKER_SOCKET', '')}",
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
    fake_docker_compose.write_text(
        fake_docker_compose.read_text(encoding="utf-8").replace(
            "#!/usr/bin/env python3",
            f"#!{sys.executable}",
            1,
        ),
        encoding="utf-8",
    )
    fake_docker_compose.chmod(0o755)


def _write_failing_python3(bin_dir):
    fake_python3 = bin_dir / "python3"
    fake_python3.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "exit 127",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_python3.chmod(0o755)


def _run_wrapper(
    tmp_path,
    *args,
    initial_state=None,
    docker_compose_available=True,
    install_standalone_compose=False,
    port_output=None,
    fake_containers=None,
    host_python3_missing=False,
    extra_env=None,
    wrapper_path=None,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log_path = tmp_path / "docker.log"
    state_path = tmp_path / "docker.state"
    image_state_path = tmp_path / "docker.image"
    state_dir = tmp_path / "state"
    _write_fake_docker(bin_dir)
    _write_fake_identity_tools(bin_dir)
    if host_python3_missing:
        _write_failing_python3(bin_dir)
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
    env["FAKE_MANAGER_INSPECT_IDENTITY"] = f'{HOST_UID}:{HOST_GID}|["3456"]'
    env["FAKE_STATE_UID"] = HOST_UID
    env["FAKE_STATE_GID"] = HOST_GID
    if port_output is not None:
        env["FAKE_DOCKER_PORT_OUTPUT"] = port_output
    if fake_containers is not None:
        env["FAKE_DOCKER_CONTAINERS_JSON"] = json.dumps(fake_containers)
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        ["bash", str(wrapper_path or WRAPPER), *args],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    log_lines = []
    if log_path.exists():
        log_lines = log_path.read_text(encoding="utf-8").splitlines()
    log_entries = [json.loads(line) for line in log_lines if line.strip()]
    return result, state_dir, log_entries


def _write_root_identity_wrapper(tmp_path):
    source = WRAPPER.read_text(encoding="utf-8")
    trusted_identity = 'MANAGER_HOST_UID="$EUID"'
    assert source.count(trusted_identity) == 1
    wrapper_path = tmp_path / "alphagsm-docker-root-test"
    wrapper_path.write_text(
        source.replace(trusted_identity, 'MANAGER_HOST_UID="0"', 1),
        encoding="utf-8",
    )
    wrapper_path.chmod(0o755)
    return wrapper_path


def test_wrapper_bootstraps_config_before_compose_command(tmp_path):
    result, state_dir, log_entries = _run_wrapper(tmp_path, "compose", "config")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    config_text = (state_dir / "alphagsm.conf").read_text(encoding="utf-8")
    assert f"alphagsm_path = {state_dir}/home" in config_text
    assert any(entry["argv"][:2] == ["compose", "version"] for entry in log_entries)
    assert any("config" in entry["argv"] for entry in log_entries)
    compose_entries = [
        entry
        for entry in log_entries
        if entry["argv"][:2] == ["compose", "version"]
        or "config" in entry["argv"]
    ]
    assert all(entry["pull_runtime_images"] == "0" for entry in compose_entries)


@pytest.mark.parametrize(
    ("docker_compose_available", "install_standalone_compose"),
    ((True, False), (False, True)),
)
def test_wrapper_passes_non_root_host_identity_and_socket_group_to_compose(
    tmp_path,
    docker_compose_available,
    install_standalone_compose,
):
    socket_path = tmp_path / "docker.sock"
    socket_path.touch()

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "config",
        docker_compose_available=docker_compose_available,
        install_standalone_compose=install_standalone_compose,
        extra_env={
            "ALPHAGSM_DOCKER_SOCKET": str(socket_path),
            "ALPHAGSM_HOST_UID": "7777",
            "ALPHAGSM_HOST_GID": "8888",
            "ALPHAGSM_DOCKER_GID": "9999",
            "FAKE_HOST_UID": "0",
            "FAKE_HOST_GID": "0",
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    compose_entries = [
        entry
        for entry in log_entries
        if "config" in entry["argv"]
    ]
    assert compose_entries
    assert all(entry["host_uid"] == HOST_UID for entry in compose_entries)
    assert all(entry["host_gid"] == HOST_GID for entry in compose_entries)
    assert all(entry["docker_gid"] == "3456" for entry in compose_entries)
    assert all(
        entry["docker_socket"] == str(socket_path)
        for entry in compose_entries
    )


def test_wrapper_raw_compose_exec_recreates_stale_manager_identity(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "exec",
        "alphagsm",
        "bash",
        initial_state="running",
        extra_env={"FAKE_MANAGER_INSPECT_IDENTITY": '0:0|["0"]'},
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"][:3]
        == [
            "inspect",
            "-f",
            "{{.Config.User}}|{{json .HostConfig.GroupAdd}}",
        ]
        for entry in log_entries
    )
    recreate_entries = [
        entry
        for entry in log_entries
        if "up" in entry["argv"] and "--force-recreate" in entry["argv"]
    ]
    assert recreate_entries
    assert all(entry["host_uid"] == HOST_UID for entry in recreate_entries)
    assert all(entry["host_gid"] == HOST_GID for entry in recreate_entries)
    assert all(entry["docker_gid"] == "3456" for entry in recreate_entries)
    assert any("exec" in entry["argv"] for entry in log_entries)


def test_wrapper_raw_compose_up_recreates_stale_manager_identity(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "up",
        "-d",
        initial_state="running",
        extra_env={
            "FAKE_MANAGER_INSPECT_IDENTITY": f'{HOST_UID}:{HOST_GID}|["4567"]',
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    up_entries = [entry for entry in log_entries if "up" in entry["argv"]]
    assert len(up_entries) == 2
    assert "--force-recreate" in up_entries[0]["argv"]
    assert "--force-recreate" not in up_entries[1]["argv"]
    assert all(entry["docker_gid"] == "3456" for entry in up_entries)


def test_wrapper_raw_compose_reuses_matching_manager_identity(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "exec",
        "alphagsm",
        "bash",
        initial_state="running",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"][:3]
        == [
            "inspect",
            "-f",
            "{{.Config.User}}|{{json .HostConfig.GroupAdd}}",
        ]
        for entry in log_entries
    )
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("exec" in entry["argv"] for entry in log_entries)


def test_wrapper_raw_compose_config_without_manager_does_not_start(tmp_path):
    result, _, log_entries = _run_wrapper(tmp_path, "compose", "config")

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"] == ["inspect", "alphagsm-manager"]
        for entry in log_entries
    )
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("config" in entry["argv"] for entry in log_entries)


def test_wrapper_raw_compose_up_without_manager_uses_trusted_identity(tmp_path):
    result, _, log_entries = _run_wrapper(tmp_path, "compose", "up", "-d")

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"] == ["inspect", "alphagsm-manager"]
        for entry in log_entries
    )
    up_entries = [entry for entry in log_entries if "up" in entry["argv"]]
    assert len(up_entries) == 1
    assert "--force-recreate" not in up_entries[0]["argv"]
    assert up_entries[0]["host_uid"] == HOST_UID
    assert up_entries[0]["host_gid"] == HOST_GID
    assert up_entries[0]["docker_gid"] == "3456"


def test_wrapper_rejects_root_manager_identity_before_compose(tmp_path):
    root_wrapper = _write_root_identity_wrapper(tmp_path)
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "compose",
        "config",
        wrapper_path=root_wrapper,
    )

    assert result.returncode != 0
    assert "refuses to run the manager container as UID 0" in result.stderr
    assert not state_dir.exists()
    assert not (state_dir / "alphagsm.conf").exists()
    assert not (state_dir / ".manager-mode").exists()
    assert log_entries == []


@pytest.mark.parametrize("command", ("start", "up"))
def test_wrapper_rejects_root_before_start_state_mutation(tmp_path, command):
    root_wrapper = _write_root_identity_wrapper(tmp_path)
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        command,
        "--develop",
        wrapper_path=root_wrapper,
    )

    assert result.returncode != 0
    assert "refuses to run the manager container as UID 0" in result.stderr
    assert not state_dir.exists()
    assert not (state_dir / "alphagsm.conf").exists()
    assert not (state_dir / ".manager-mode").exists()
    assert log_entries == []


def test_wrapper_rejects_root_before_manager_reuse_or_pull(tmp_path):
    root_wrapper = _write_root_identity_wrapper(tmp_path)
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        wrapper_path=root_wrapper,
    )

    assert result.returncode != 0
    assert "refuses to run the manager container as UID 0" in result.stderr
    assert not state_dir.exists()
    assert not (state_dir / "alphagsm.conf").exists()
    assert not (state_dir / ".manager-mode").exists()
    assert log_entries == []


def test_wrapper_reuses_running_manager_with_matching_identity(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"][:3]
        == [
            "inspect",
            "-f",
            "{{.Config.User}}|{{json .HostConfig.GroupAdd}}",
        ]
        for entry in log_entries
    )
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert any("exec" in entry["argv"] for entry in log_entries)


def test_wrapper_recreates_running_root_manager(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={"FAKE_MANAGER_INSPECT_IDENTITY": '0:0|["0"]'},
    )

    assert result.returncode == 0, result.stderr or result.stdout
    recreate_entries = [
        entry
        for entry in log_entries
        if "up" in entry["argv"]
    ]
    assert recreate_entries
    assert all("--force-recreate" in entry["argv"] for entry in recreate_entries)
    assert all(entry["host_uid"] == HOST_UID for entry in recreate_entries)
    assert all(entry["host_gid"] == HOST_GID for entry in recreate_entries)


def test_wrapper_recreates_running_manager_with_mismatched_docker_group(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={
            "FAKE_MANAGER_INSPECT_IDENTITY": f'{HOST_UID}:{HOST_GID}|["4567"]',
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    recreate_entries = [
        entry
        for entry in log_entries
        if "up" in entry["argv"]
    ]
    assert recreate_entries
    assert all("--force-recreate" in entry["argv"] for entry in recreate_entries)
    assert all(entry["docker_gid"] == "3456" for entry in recreate_entries)


def test_wrapper_preserves_root_owned_state_before_stale_identity_recreation(
    tmp_path,
):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    config_path = state_dir / "alphagsm.conf"
    mode_path = state_dir / ".manager-mode"
    config_path.write_text("preserve-this-config\n", encoding="utf-8")
    mode_path.write_text("release\n", encoding="utf-8")

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={
            "ALPHAGSM_HOST_UID": "0",
            "ALPHAGSM_HOST_GID": "0",
            "FAKE_MANAGER_INSPECT_IDENTITY": '0:0|["0"]',
            "FAKE_STATE_UID": "0",
            "FAKE_STATE_GID": "0",
        },
    )

    assert result.returncode != 0
    assert str(state_dir) in result.stderr
    assert f"sudo chown -R {HOST_UID}:{HOST_GID}" in result.stderr
    assert config_path.read_text(encoding="utf-8") == "preserve-this-config\n"
    assert mode_path.read_text(encoding="utf-8") == "release\n"
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)


def test_wrapper_rejects_state_tree_symlink_before_stale_identity_recreation(
    tmp_path,
):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "alphagsm.conf").write_text("preserve\n", encoding="utf-8")
    target_dir = tmp_path / "outside-state"
    target_dir.mkdir()
    target_file = target_dir / "sentinel"
    target_file.write_text("untouched\n", encoding="utf-8")
    (state_dir / "linked-state").symlink_to(target_dir, target_is_directory=True)

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={"FAKE_MANAGER_INSPECT_IDENTITY": '0:0|["0"]'},
    )

    assert result.returncode != 0
    assert str(state_dir / "linked-state") in result.stderr
    assert "symbolic link" in result.stderr
    assert target_file.read_text(encoding="utf-8") == "untouched\n"
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)


@pytest.mark.parametrize("socket_selector", ("explicit", "docker-host"))
def test_wrapper_recreates_manager_when_docker_socket_source_changes(
    tmp_path,
    socket_selector,
):
    old_socket = tmp_path / "old-docker.sock"
    new_socket = tmp_path / "new-docker.sock"
    old_socket.touch()
    new_socket.touch()
    extra_env = {
        "FAKE_MANAGER_INSPECT_SOCKET_SOURCE": str(old_socket),
    }
    if socket_selector == "explicit":
        extra_env["ALPHAGSM_DOCKER_SOCKET"] = str(new_socket)
    else:
        extra_env["DOCKER_HOST"] = f"unix://{new_socket}"

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env=extra_env,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"][:3]
        == [
            "inspect",
            "-f",
            '{{range .Mounts}}{{if eq .Destination "/var/run/docker.sock"}}'
            "{{println .Source}}{{end}}{{end}}",
        ]
        for entry in log_entries
    )
    recreate_entries = [
        entry
        for entry in log_entries
        if "up" in entry["argv"] and "--force-recreate" in entry["argv"]
    ]
    assert recreate_entries
    assert all(entry["docker_gid"] == "3456" for entry in recreate_entries)
    assert all(
        entry["docker_socket"] == str(new_socket)
        for entry in recreate_entries
    )


@pytest.mark.parametrize("inspected_source", ("", "/one.sock\n/two.sock"))
def test_wrapper_recreates_manager_when_socket_mount_inspection_is_not_unique(
    tmp_path,
    inspected_source,
):
    socket_path = tmp_path / "docker.sock"
    socket_path.touch()

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={
            "ALPHAGSM_DOCKER_SOCKET": str(socket_path),
            "FAKE_MANAGER_INSPECT_SOCKET_SOURCE": inspected_source,
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    recreate_entries = [
        entry
        for entry in log_entries
        if "up" in entry["argv"] and "--force-recreate" in entry["argv"]
    ]
    assert recreate_entries


def test_wrapper_normalizes_expected_socket_source_before_manager_reuse(tmp_path):
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()
    socket_path = socket_dir / "docker.sock"
    socket_path.touch()
    unnormalized_socket = socket_dir / ".." / "sockets" / "docker.sock"

    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "status",
        initial_state="running",
        extra_env={
            "ALPHAGSM_DOCKER_SOCKET": str(unnormalized_socket),
            "FAKE_MANAGER_INSPECT_SOCKET_SOURCE": str(socket_path),
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert any(
        entry["argv"][:3]
        == [
            "inspect",
            "-f",
            '{{range .Mounts}}{{if eq .Destination "/var/run/docker.sock"}}'
            "{{println .Source}}{{end}}{{end}}",
        ]
        for entry in log_entries
    )
    assert not any("up" in entry["argv"] for entry in log_entries)
    exec_entries = [entry for entry in log_entries if "exec" in entry["argv"]]
    assert exec_entries
    assert all(
        entry["docker_socket"] == str(socket_path)
        for entry in exec_entries
    )


def test_wrapper_help_includes_ps_usage(tmp_path):
    result, _, log_entries = _run_wrapper(tmp_path, "help")

    assert result.returncode == 0, result.stderr or result.stdout
    assert "  ./alphagsm-docker ps" in result.stdout
    assert log_entries == []


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
            "logs": "[alpha] booting\\n[alpha] ready",
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
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["inspect"] for entry in log_entries)
    assert "Recent container logs (last 10 lines):" in result.stdout
    assert "[alpha] booting" in result.stdout
    assert "[alpha] ready" in result.stdout
    assert "Detach with Ctrl-p Ctrl-q" in result.stdout
    assert "ATTACHED:custom-demo" in result.stdout
    assert any(entry["argv"][:1] == ["logs"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)


def test_wrapper_connect_supports_tail_override(tmp_path):
    fake_containers = {
        "custom-demo": {
            "state": "running",
            "logs": "[alpha] line one",
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
        "--tail",
        "25",
        fake_containers=fake_containers,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Recent container logs (last 25 lines):" in result.stdout
    assert any(entry["argv"][:2] == ["logs", "--tail"] and entry["argv"][2] == "25" for entry in log_entries)


def test_wrapper_connect_supports_no_logs(tmp_path):
    fake_containers = {
        "custom-demo": {
            "state": "running",
            "logs": "[alpha] should not print",
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
        "--no-logs",
        fake_containers=fake_containers,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Recent container logs" not in result.stdout
    assert not any(entry["argv"][:1] == ["logs"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["attach"] for entry in log_entries)


def test_wrapper_connect_supports_custom_detach_keys(tmp_path):
    fake_containers = {
        "custom-demo": {
            "state": "running",
            "logs": "[alpha] ready",
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
        "--detach-keys",
        "ctrl-z,z",
        fake_containers=fake_containers,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Detach with Docker escape sequence: ctrl-z,z" in result.stdout
    assert any(
        entry["argv"][:3] == ["attach", "--detach-keys", "ctrl-z,z"]
        for entry in log_entries
    )


def test_wrapper_connect_supports_custom_detach_keys_from_env(tmp_path):
    fake_containers = {
        "custom-demo": {
            "state": "running",
            "logs": "[alpha] ready",
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
        extra_env={"ALPHAGSM_CONNECT_DETACH_KEYS": "ctrl-z,z"},
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Detach with Docker escape sequence: ctrl-z,z" in result.stdout
    assert any(
        entry["argv"][:3] == ["attach", "--detach-keys", "ctrl-z,z"]
        for entry in log_entries
    )


def test_wrapper_connect_forwards_non_docker_server_through_manager_exec(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(state_dir, "demo", {"runtime": "process"})
    result, _, log_entries = _run_wrapper(tmp_path, "demo", "connect", "--no-logs", "--tail", "25")

    assert result.returncode == 0, result.stderr or result.stdout
    assert not any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert any("exec" in entry["argv"] for entry in log_entries)
    assert "FORWARDED:-T alphagsm python alphagsm demo connect" in result.stdout


def test_wrapper_connect_rejects_missing_docker_container(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    result, _, log_entries = _run_wrapper(tmp_path, "demo", "connect")

    assert result.returncode != 0
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["inspect"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)
    assert "Container 'custom-demo' was not found." in result.stderr
    assert "demo status" in result.stderr
    assert "demo start" in result.stderr


def test_wrapper_connect_rejects_stopped_docker_container(tmp_path):
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
        fake_containers={"custom-demo": {"state": "stopped"}},
    )

    assert result.returncode != 0
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert any(entry["argv"][:1] == ["inspect"] for entry in log_entries)
    assert not any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)
    assert "Container 'custom-demo' is not running." in result.stderr
    assert "demo start" in result.stderr


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


@pytest.mark.parametrize("alphagsm_command", ["status", "start"])
def test_wrapper_uses_metadata_container_name_for_host_connection_details(
    tmp_path,
    alphagsm_command,
):
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        alphagsm_command,
        initial_state="running",
        fake_containers={
            "custom-demo": {
                "state": "running",
                "ports": "25565/tcp -> 0.0.0.0:25565",
            },
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Host connection details:" in result.stdout
    assert "25565/tcp -> 0.0.0.0:25565" in result.stdout
    assert any(
        entry["argv"][:1] == ["port"] and entry["argv"][-1] == "custom-demo"
        for entry in log_entries
    )
    assert not any(
        entry["argv"][:1] == ["port"] and entry["argv"][-1] == "alphagsm-demo"
        for entry in log_entries
    )


def test_wrapper_ps_requires_host_python3(tmp_path):
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "ps",
        host_python3_missing=True,
    )

    assert result.returncode != 0
    assert "Host python3 is required for './alphagsm-docker ps'" in result.stderr
    assert log_entries == []


def test_wrapper_connect_falls_back_to_forwarded_exec_when_host_python3_is_missing(tmp_path):
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
        "--tail=3",
        host_python3_missing=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert not any(entry["argv"][:1] == ["attach"] for entry in log_entries)
    assert any("exec" in entry["argv"] for entry in log_entries)
    assert "FORWARDED:-T alphagsm python alphagsm demo connect" in result.stdout


def test_wrapper_connect_rejects_unknown_option(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    result, _, log_entries = _run_wrapper(tmp_path, "demo", "connect", "--bogus")

    assert result.returncode != 0
    assert "Unknown option for connect: --bogus" in result.stderr
    assert log_entries == []


def test_wrapper_builds_locally_when_remote_pull_fails(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_fake_docker(bin_dir)
    _write_fake_identity_tools(bin_dir)
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


def test_wrapper_ps_lists_docker_backed_servers_in_current_home(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    _write_server_config(
        state_dir,
        "vanilla",
        {"runtime": "process"},
    )
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "ps",
        fake_containers={
            "custom-demo": {
                "state": "running",
                "ports": "25565/tcp -> 0.0.0.0:25565",
            }
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert any(line.startswith("SERVER") for line in lines), result.stdout
    server_line = next(
        (line for line in lines if "demo" in line and "custom-demo" in line),
        None,
    )
    assert server_line is not None, result.stdout
    assert "running" in server_line
    assert "25565/tcp -> 0.0.0.0:25565" in server_line
    assert not any("vanilla" in line for line in lines)


def test_wrapper_ps_reports_empty_state_when_no_docker_servers_exist(tmp_path):
    result, _, log_entries = _run_wrapper(tmp_path, "ps")

    assert result.returncode == 0, result.stderr or result.stdout
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)
    assert result.stdout.splitlines() == [
        "No Docker-backed AlphaGSM servers found in the current wrapper home."
    ]


def test_wrapper_ps_keeps_port_mappings_for_stopped_containers(tmp_path):
    state_dir = tmp_path / "state"
    _write_server_config(
        state_dir,
        "demo",
        {"runtime": "docker", "container_name": "custom-demo"},
    )
    result, _, log_entries = _run_wrapper(
        tmp_path,
        "ps",
        fake_containers={
            "custom-demo": {
                "state": "stopped",
                "ports": "25565/tcp -> 0.0.0.0:25565",
            }
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert not any(entry["argv"][:1] == ["pull"] for entry in log_entries)
    assert not any("up" in entry["argv"] for entry in log_entries)
    assert not any("exec" in entry["argv"] for entry in log_entries)

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    server_line = next(
        (line for line in lines if "demo" in line and "custom-demo" in line),
        None,
    )
    assert server_line is not None, result.stdout
    assert "stopped" in server_line
    assert "25565/tcp -> 0.0.0.0:25565" in server_line
