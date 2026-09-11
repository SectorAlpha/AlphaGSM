"""Failure-path tests for the deferred executable replacement transaction."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def update_job(tmp_path):
    target = tmp_path / "AlphaGSM & spaces.exe"
    target.write_bytes(b"old")
    stage = tmp_path / ".alphagsm-self-update-test"
    stage.mkdir()
    (stage / "replacement.exe").write_bytes(b"new")
    job = stage / "job.json"
    job.write_text(json.dumps({
        "target": str(target),
        "sha256": hashlib.sha256(b"new").hexdigest(),
        "parent_pid": 1234,
    }), encoding="utf-8")
    return job, target


def helper():
    return importlib.import_module("core.binary_update")


def test_deferred_update_waits_for_parent_before_replacing(monkeypatch, update_job):
    module = helper()
    job, target = update_job
    calls = []

    def wait(pid, timeout):
        assert target.read_bytes() == b"old"
        calls.append((pid, timeout))

    monkeypatch.setattr(module, "_wait_for_parent_exit", wait)
    assert module.complete_update(job) == 0
    assert calls == [(1234, 120)]
    assert target.read_bytes() == b"new"
    assert "Updated" in (job.parent / "result.txt").read_text()
    assert not (job.parent / "backup.exe").exists()
    assert not (job.parent / "replacement.exe").exists()


def test_deferred_update_parent_timeout_never_replaces(monkeypatch, update_job):
    module = helper()
    job, target = update_job

    def timeout(*_args):
        raise TimeoutError("parent is still running")

    monkeypatch.setattr(module, "_wait_for_parent_exit", timeout)
    assert module.complete_update(job) == 1
    assert target.read_bytes() == b"old"
    assert "parent is still running" in (job.parent / "result.txt").read_text()
    assert not (job.parent / "replacement.exe").exists()


def test_deferred_update_rechecks_checksum_after_parent_exit(monkeypatch, update_job):
    module = helper()
    job, target = update_job
    monkeypatch.setattr(module, "_wait_for_parent_exit", lambda *_args: None)
    (job.parent / "replacement.exe").write_bytes(b"tampered")
    assert module.complete_update(job) == 1
    assert target.read_bytes() == b"old"
    assert "SHA256" in (job.parent / "result.txt").read_text()


def test_deferred_update_restores_backup_after_failed_install(monkeypatch, update_job):
    module = helper()
    job, target = update_job
    monkeypatch.setattr(module, "_wait_for_parent_exit", lambda *_args: None)
    monkeypatch.setattr(module, "REPLACE_ATTEMPTS", 2)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    replace = module.os.replace

    def fail_install(source, destination):
        if Path(source).name == "replacement.exe":
            raise PermissionError("locked")
        return replace(source, destination)

    monkeypatch.setattr(module.os, "replace", fail_install)
    assert module.complete_update(job) == 1
    assert target.read_bytes() == b"old"
    assert "locked" in (job.parent / "result.txt").read_text()
    assert not (job.parent / "backup.exe").exists()


def test_deferred_update_preserves_backup_if_rollback_fails(monkeypatch, update_job):
    module = helper()
    job, target = update_job
    monkeypatch.setattr(module, "_wait_for_parent_exit", lambda *_args: None)
    monkeypatch.setattr(module, "REPLACE_ATTEMPTS", 1)
    replace = module.os.replace

    def fail_install_and_rollback(source, destination):
        if Path(destination) == target:
            raise PermissionError("locked")
        return replace(source, destination)

    monkeypatch.setattr(module.os, "replace", fail_install_and_rollback)
    assert module.complete_update(job) == 1
    assert (job.parent / "backup.exe").read_bytes() == b"old"
    result = (job.parent / "result.txt").read_text()
    assert "restore" in result.lower()
    assert str(job.parent / "backup.exe") in result


def test_deferred_update_rejects_target_outside_stage_parent(monkeypatch, update_job, tmp_path):
    module = helper()
    job, _target = update_job
    outside = tmp_path / "other" / "victim.exe"
    outside.parent.mkdir()
    outside.write_bytes(b"untouched")
    data = json.loads(job.read_text())
    data["target"] = str(outside)
    job.write_text(json.dumps(data))
    monkeypatch.setattr(module, "_wait_for_parent_exit", lambda *_args: None)
    assert module.complete_update(job) == 1
    assert outside.read_bytes() == b"untouched"


def test_invalid_job_does_not_clean_unrelated_files(tmp_path):
    module = helper()
    payload = tmp_path / "replacement.exe"
    payload.write_bytes(b"unrelated")
    assert module.complete_update(tmp_path / "missing.json") == 1
    assert payload.read_bytes() == b"unrelated"
    assert not (tmp_path / "result.txt").exists()


def test_schedule_uses_argv_and_independent_frozen_environment(monkeypatch, update_job):
    module = helper()
    job, target = update_job
    launches = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda args, **kwargs: launches.append((args, kwargs)))
    checksum = hashlib.sha256(b"new").hexdigest()
    result = module.schedule_update(target, job.parent, checksum)
    assert result == job.parent / "result.txt"
    args, kwargs = launches[0]
    assert args == [str(job.parent / "helper.exe"), "--_complete-self-update", str(job)]
    assert kwargs.get("shell", False) is False
    assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert (job.parent / "helper.exe").read_bytes() == b"old"
    assert json.loads(job.read_text())["sha256"] == checksum
    assert "scheduled" in result.read_text()
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("result, expected_exception", [(0, None), (0x102, TimeoutError), (0xFFFFFFFF, OSError)])
def test_windows_wait_closes_process_handle(monkeypatch, result, expected_exception):
    from types import SimpleNamespace
    from unittest.mock import Mock

    module = helper()
    kernel = SimpleNamespace(OpenProcess=Mock(return_value=123),
                             WaitForSingleObject=Mock(return_value=result),
                             CloseHandle=Mock())
    monkeypatch.setattr(module.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    monkeypatch.setattr(module.ctypes, "get_last_error", lambda: 5, raising=False)
    if expected_exception:
        with pytest.raises(expected_exception):
            module._wait_for_parent_exit(4321, 120)
    else:
        module._wait_for_parent_exit(4321, 120)
    kernel.OpenProcess.assert_called_once_with(0x00100000, False, 4321)
    kernel.WaitForSingleObject.assert_called_once_with(123, 120000)
    kernel.CloseHandle.assert_called_once_with(123)


@pytest.mark.parametrize("error, expected_exception", [(87, None), (5, OSError)])
def test_windows_wait_handles_missing_or_inaccessible_parent(monkeypatch, error, expected_exception):
    from types import SimpleNamespace
    from unittest.mock import Mock

    module = helper()
    kernel = SimpleNamespace(OpenProcess=Mock(return_value=0),
                             WaitForSingleObject=Mock(), CloseHandle=Mock())
    monkeypatch.setattr(module.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    monkeypatch.setattr(module.ctypes, "get_last_error", lambda: error, raising=False)
    if expected_exception:
        with pytest.raises(expected_exception):
            module._wait_for_parent_exit(4321, 120)
    else:
        module._wait_for_parent_exit(4321, 120)
    kernel.WaitForSingleObject.assert_not_called()
    kernel.CloseHandle.assert_not_called()


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="requires native Windows process handles")
def test_wait_for_real_windows_process_exit():
    import subprocess
    import sys

    module = helper()
    with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.2)"]) as process:
        module._wait_for_parent_exit(process.pid, 10)
        assert process.wait(timeout=1) == 0
