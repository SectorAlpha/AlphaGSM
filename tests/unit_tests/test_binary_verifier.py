"""Regression coverage for the artifact acceptance harness isolation."""

import os
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


def test_verifier_configuration_uses_normal_user_lookup(tmp_path):
    binary = tmp_path / "alphagsm"
    binary.touch()
    runner = verify_binary.BinaryRunner(binary, tmp_path / "acceptance")
    config = runner.configure("process", "subprocess")
    expected = runner.home / ("AppData/Local/alphagsm" if os.name == "nt" else ".alphagsm")
    assert config == expected / "alphagsm.conf"
    assert "backend = subprocess" in config.read_text()
    assert "ALPHAGSM_CONFIG_LOCATION" not in runner.env


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
