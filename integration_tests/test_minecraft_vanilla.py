import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request

import pytest


pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
TEST_TIMEOUT_SECONDS = 600
START_TIMEOUT_SECONDS = 180
STOP_TIMEOUT_SECONDS = 90


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _write_config(config_path, home_dir):
    config_path.write_text(
        "\n".join(
            [
                "[core]",
                f"alphagsm_path = {home_dir}",
                f"userconf = {home_dir}",
                "",
                "[downloader]",
                f"db_path = {home_dir / 'downloads' / 'downloads.txt'}",
                f"target_path = {home_dir / 'downloads' / 'downloads'}",
                "",
                "[server]",
                f"datapath = {home_dir / 'conf'}",
                "",
                "[screen]",
                f"screenlog_path = {home_dir / 'logs'}",
                "sessiontag = AlphaGSM-IT#",
                "keeplogs = 1",
                "",
            ]
        )
        + "\n"
    )


def _write_java_wrapper(wrapper_path):
    wrapper_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'exec java -Xms256M -Xmx768M "$@"',
                "",
            ]
        )
    )
    wrapper_path.chmod(0o755)


def _fetch_latest_release_server_url():
    with urllib.request.urlopen(MANIFEST_URL, timeout=30) as response:
        manifest = json.loads(response.read().decode("utf-8"))
    latest_release = manifest["latest"]["release"]
    version_url = next(
        version["url"]
        for version in manifest["versions"]
        if version["id"] == latest_release
    )
    with urllib.request.urlopen(version_url, timeout=30) as response:
        version_data = json.loads(response.read().decode("utf-8"))
    return latest_release, version_data["downloads"]["server"]["url"]


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def _run_alphagsm(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    command = [sys.executable, str(ALPHAGSM_SCRIPT)] + list(args)
    return subprocess.run(
        command,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _log_command_result(name, result):
    print(f"\n=== {name} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(result.stdout.rstrip())
    if result.stderr:
        print("stderr:")
        print(result.stderr.rstrip())


def _run_and_assert_ok(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    result = _run_alphagsm(env, *args, timeout=timeout)
    _log_command_result("alphagsm " + " ".join(args), result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _encode_varint(value):
    buf = bytearray()
    while True:
        temp = value & 0x7F
        value >>= 7
        if value != 0:
            temp |= 0x80
        buf.append(temp)
        if value == 0:
            return bytes(buf)


def _read_varint(sock):
    num_read = 0
    result = 0
    while True:
        raw = sock.recv(1)
        if not raw:
            raise ConnectionError("Connection closed while reading VarInt")
        value = raw[0]
        result |= (value & 0x7F) << (7 * num_read)
        num_read += 1
        if num_read > 5:
            raise ValueError("VarInt too large")
        if value & 0x80 == 0:
            return result


def _minecraft_status_ping(host, port, timeout=5):
    with socket.create_connection((host, port), timeout=timeout) as sock:
        handshake_data = b"".join(
            [
                _encode_varint(0),
                _encode_varint(760),
                _encode_varint(len(host)),
                host.encode("utf-8"),
                struct.pack(">H", port),
                _encode_varint(1),
            ]
        )
        sock.sendall(_encode_varint(len(handshake_data)) + handshake_data)
        sock.sendall(_encode_varint(1) + _encode_varint(0))

        _read_varint(sock)
        packet_id = _read_varint(sock)
        if packet_id != 0:
            raise ValueError(f"Unexpected status packet id: {packet_id}")
        payload_length = _read_varint(sock)
        payload = b""
        while len(payload) < payload_length:
            chunk = sock.recv(payload_length - len(payload))
            if not chunk:
                raise ConnectionError("Connection closed while reading status payload")
            payload += chunk
    return json.loads(payload.decode("utf-8"))


def _wait_for_status(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            return _minecraft_status_ping(host, port, timeout=3)
        except Exception as ex:  # noqa: BLE001 - integration polling
            last_error = ex
            time.sleep(2)
    raise AssertionError(f"Minecraft server did not respond in time: {last_error}")


def _wait_for_port_to_close(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            _minecraft_status_ping(host, port, timeout=2)
        except Exception:  # noqa: BLE001 - any failure means the server is no longer responding
            return
        time.sleep(2)
    raise AssertionError("Minecraft server still responds after stop timeout")


def test_minecraft_vanilla_download_install_and_start(tmp_path):
    _require_integration_opt_in()
    _require_command("java")
    _require_command("screen")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "minecraft-server"
    config_path = tmp_path / "alphagsm-integration.conf"
    wrapper_path = tmp_path / "java-wrapper.sh"
    server_name = "itmc"
    port = _pick_free_port()

    home_dir.mkdir()
    _write_config(config_path, home_dir)
    _write_java_wrapper(wrapper_path)
    release_id, server_url = _fetch_latest_release_server_url()
    env = _alphagsm_env(config_path)

    _run_and_assert_ok(env, server_name, "create", "minecraft.vanilla")

    _run_and_assert_ok(env, server_name, "set", "javapath", str(wrapper_path))

    _run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        "-l",
        str(port),
        str(install_dir),
        "-u",
        server_url,
        timeout=TEST_TIMEOUT_SECONDS,
    )

    jar_path = install_dir / "minecraft_server.jar"
    assert jar_path.exists(), f"Expected downloaded jar at {jar_path}"
    assert (install_dir / "eula.txt").exists()
    assert (install_dir / "server.properties").exists()

    _run_and_assert_ok(env, server_name, "start", timeout=60)

    try:
        status = _wait_for_status("127.0.0.1", port, START_TIMEOUT_SECONDS)
        assert status["version"]["name"]
        assert release_id.split(".")[0] in status["version"]["name"]
        status_cmd = _run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_cmd.stdout
        _run_and_assert_ok(env, server_name, "message", "hello world")
    finally:
        _run_and_assert_ok(env, server_name, "stop", timeout=STOP_TIMEOUT_SECONDS)
        _wait_for_port_to_close("127.0.0.1", port, STOP_TIMEOUT_SECONDS)
        final_status = _run_and_assert_ok(env, server_name, "status")
        assert "isn't running" in final_status.stdout
