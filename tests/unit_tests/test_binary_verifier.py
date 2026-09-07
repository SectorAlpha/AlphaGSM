"""Regression coverage for the artifact acceptance harness isolation."""

import os
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts import verify_binary


def test_artifact_environment_removes_checkout_and_python_configuration(tmp_path):
    env = verify_binary.clean_environment(tmp_path, {
        "PATH": "/usr/bin", "HOME": "/old/home", "PYTHONPATH": "/checkout/src",
        "PYTHONHOME": "/venv", "VIRTUAL_ENV": "/venv",
        "ALPHAGSM_CONFIG_LOCATION": "/checkout/test.conf",
        "ALPHAGSM_USERCONFIG_LOCATION": "/old/user.conf",
        "ALPHAGSM_VERSION": "wrong", "_PYI_APPLICATION_HOME_DIR": "/old/bundle",
    })
    assert env["HOME"] == str(tmp_path)
    assert env["USERPROFILE"] == str(tmp_path)
    assert env["LOCALAPPDATA"] == str(tmp_path / "AppData" / "Local")
    assert env["PATH"] == "/usr/bin"
    assert not any(key.startswith(("PYTHON", "ALPHAGSM_", "_PYI_")) for key in env)
    assert "VIRTUAL_ENV" not in env


def test_verifier_executes_copied_artifact_directly(tmp_path, monkeypatch):
    original = tmp_path / "release" / "alphagsm"
    original.parent.mkdir()
    original.write_bytes(b"artifact bytes")
    work = tmp_path / "acceptance"
    runner = verify_binary.BinaryRunner(original, work)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "AlphaGSM 1.0", "")

    monkeypatch.setattr(verify_binary.subprocess, "run", run)
    runner.run("--version")
    command, kwargs = calls[0]
    assert command == [str(work / "bin with spaces é" / "alphagsm"), "--version"]
    assert Path(command[0]).read_bytes() == original.read_bytes()
    assert kwargs["cwd"] == work / "unrelated working directory é"
    assert not any(key.startswith("ALPHAGSM_") for key in kwargs["env"])


def test_artifact_failure_is_not_a_success(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    monkeypatch.setattr(verify_binary.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, "", "missing bundled data"))
    with pytest.raises(RuntimeError, match="missing bundled data"):
        runner.run("probe", "create", "gmodserver")


def test_command_timeout_keeps_partial_output_in_owned_evidence(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1, output=b"startup evidence", stderr=b"last error")

    monkeypatch.setattr(verify_binary.subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run("binarymc", "start", timeout=1)
    transcript = (runner.evidence / "commands.log").read_text()
    assert "startup evidence" in transcript
    assert "last error" in transcript


def test_failure_snapshot_is_not_overwritten_after_stop(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    runner.last_server = "binarymc"
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, '{"before_stop":true}', "")

    monkeypatch.setattr(runner, "run", run)
    runner.capture_failure()
    runner.capture_failure()
    assert len(calls) == 2
    assert json.loads((runner.evidence / "failure-doctor.json").read_text())["before_stop"]


def test_verifier_configuration_uses_normal_user_lookup(tmp_path):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    config = runner.configure("process", "subprocess")
    expected = runner.home / ("AppData/Local/alphagsm" if os.name == "nt" else ".alphagsm")
    assert config == expected / "alphagsm.conf"
    assert "backend = subprocess" in config.read_text()
    assert "ALPHAGSM_CONFIG_LOCATION" not in runner.env
    system_config = (runner.binary.parent / "alphagsm.conf").read_text()
    assert f"db_path = {expected / 'downloads/db.txt'}" in system_config
    assert f"target_path = {expected / 'downloads/files'}" in system_config


def test_failure_evidence_uses_owned_directory_and_never_scans_server_files(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    runner.configure("docker", "subprocess")
    runner.last_server = "binarymc"
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        output = '{"status":"failed","runtime":{"container_running":true}}' if "doctor" in command else "last console output"
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(verify_binary.subprocess, "run", run)
    monkeypatch.setattr(Path, "rglob", lambda *args: (_ for _ in ()).throw(AssertionError("must not scan game world")))
    runner.capture_failure()
    evidence = runner.work / "evidence"
    assert json.loads((evidence / "failure-doctor.json").read_text())["runtime"]["container_running"]
    assert "last console output" in (evidence / "failure-console.log").read_text()
    assert "last console output" in (evidence / "failure-docker.log").read_text()
    assert any(command[:4] == ["docker", "logs", "--tail", "100"] for command in calls)


def test_lifecycle_captures_failure_before_stopping_container(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    jar = tmp_path / "server.jar"
    jar.write_bytes(b"fixture")
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    events = []

    def run(*args, **kwargs):
        events.append(args[1])
        if args[1] == "setup":
            install = runner.work / "minecraft-server"
            install.mkdir()
            for filename in ("minecraft_server.jar", "eula.txt", "server.properties"):
                (install / filename).touch()
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(runner, "run", run)
    monkeypatch.setattr(runner, "capture_failure", lambda: events.append("capture"))
    monkeypatch.setattr(verify_binary, "free_port", lambda: 25565)
    monkeypatch.setattr(verify_binary, "wait_for_info", lambda *args: (_ for _ in ()).throw(RuntimeError("readiness failed")))
    with pytest.raises(RuntimeError, match="readiness failed"):
        verify_binary.verify_lifecycle(runner, jar, "java", 1, "docker", None)
    assert events.index("capture") < events.index("stop")


def test_console_proof_reads_public_logs_without_scanning_root_owned_world(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    jar = tmp_path / "server.jar"
    jar.write_bytes(b"fixture")
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        if args[1] == "setup":
            install = runner.work / "minecraft-server"
            install.mkdir()
            for filename in ("minecraft_server.jar", "eula.txt", "server.properties"):
                (install / filename).touch()
        output = {
            "status": "Server isn't running" if any(call[1] == "stop" for call in calls) else "Server is running",
            "query": "Server port is open", "info": "Server info (SLP",
            "logs": "[Server thread/INFO]: [Server] binary-console-control-confirmed",
        }.get(args[1], "")
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(runner, "run", run)
    monkeypatch.setattr(verify_binary, "free_port", lambda: 25565)
    monkeypatch.setattr(verify_binary, "wait_for_info", lambda *args: None)
    monkeypatch.setattr(verify_binary.socket, "create_connection", lambda *args, **kwargs:
                        (_ for _ in ()).throw(ConnectionRefusedError()))
    monkeypatch.setattr(Path, "rglob", lambda *args: (_ for _ in ()).throw(PermissionError("root-owned world")))
    verify_binary.verify_lifecycle(runner, jar, "java", 1, "docker", None)
    assert ("binarymc", "logs", "-n", "100") in calls


def test_workflow_uploads_only_owned_evidence_directories():
    workflow = Path(".github/workflows/binary.yml").read_text()
    assert "binary-evidence/evidence/" in workflow
    assert "binary-docker-evidence/evidence/" in workflow
    assert "binary-docker-evidence/**/*.log" not in workflow


def test_windows_updater_probe_boots_the_copied_native_executable(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm.exe"
    binary.write_bytes(b"built executable")
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    monkeypatch.setattr(verify_binary.subprocess, "Popen", lambda command, **kwargs:
                        SimpleNamespace(pid=12345, communicate=lambda timeout: ("", ""), returncode=0))
    calls = []

    def run(command, **kwargs):
        import json
        calls.append((command, kwargs))
        manifest = Path(command[-1])
        payload = json.loads(manifest.read_text())
        assert payload["parent_pid"] == 12345
        stage = manifest.parent
        (stage / "replacement.exe").replace(payload["target"])
        (stage / "result.txt").write_text("Updated AlphaGSM binary successfully")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(verify_binary.subprocess, "run", run)
    verify_binary.verify_windows_updater(runner)
    command, kwargs = calls[0]
    assert command[1] == "--_complete-self-update"
    assert Path(command[0]).name == "helper.exe"
    assert Path(command[0]).read_bytes() == binary.read_bytes()
    assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert "ALPHAGSM_CONFIG_LOCATION" not in kwargs["env"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory permission contract")
def test_acceptance_uses_read_only_unicode_binary_directory_and_restores_permissions(tmp_path, monkeypatch):
    binary = tmp_path / "alphagsm"
    binary.touch()
    work = tmp_path / "acceptance"
    monkeypatch.setattr(verify_binary.sys, "argv", ["verify_binary.py", str(binary),
                        "--resources-only", "--work-dir", str(work)])
    monkeypatch.setattr(verify_binary.BinaryRunner, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess([], 0, "AlphaGSM test", ""))
    observed = []

    def check_permissions(runner):
        observed.append(runner.binary.parent)
        assert " " in str(runner.binary)
        assert "é" in str(runner.binary)
        assert runner.binary.parent.stat().st_mode & 0o222 == 0

    monkeypatch.setattr(verify_binary, "verify_resources", check_permissions)
    verify_binary.main()
    assert observed[0].stat().st_mode & 0o700 == 0o700


def test_resource_acceptance_exercises_bulk_worker_commands(tmp_path):
    import json
    calls = []
    def run(*args):
        calls.append(args)
        if args[:3] == ('template', 'set', 'servername'):
            (tmp_path / 'template-server/DedicatedServerConfig.json').write_text(json.dumps({'LobbyConfig': {'Name': 'test'}}))
        return SimpleNamespace(stdout='resource0\nresource1\n')
    runner = SimpleNamespace(work=tmp_path, run=run)
    verify_binary.verify_resources(runner)
    assert ('2', 'resource0', 'resource1', 'list') in calls
    assert ('2', 'resource0', 'resource1', 'status') in calls
