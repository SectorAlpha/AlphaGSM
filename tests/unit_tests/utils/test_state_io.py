"""Atomic file and process lock guarantees for local server state."""

import importlib
import os
import subprocess
import sys

import pytest


def state_io():
    return importlib.import_module("utils.state_io")


def test_atomic_write_failure_keeps_previous_file_and_removes_temp(monkeypatch, tmp_path):
    module = state_io()
    path = tmp_path / "state.json"
    path.write_text('{"old": true}')

    def fail_replace(*_args):
        raise PermissionError("replacement denied")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(PermissionError):
        module.atomic_write_text(path, '{"new": true}')
    assert path.read_text() == '{"old": true}'
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_write_preserves_permissions_and_syncs_before_replace(monkeypatch, tmp_path):
    module = state_io()
    path = tmp_path / "state.json"
    path.write_text("old")
    path.chmod(0o640)
    calls = []
    replace = module.os.replace
    fsync = module.os.fsync
    monkeypatch.setattr(module.os, "fsync", lambda fd: (calls.append("fsync"), fsync(fd))[1])
    monkeypatch.setattr(module.os, "replace", lambda source, target: (calls.append("replace"), replace(source, target))[1])
    module.atomic_write_text(path, "new")
    assert path.read_text() == "new"
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o640
    assert calls.index("fsync") < calls.index("replace")


def test_state_lock_is_reentrant_and_times_out_in_other_process(tmp_path):
    module = state_io()
    path = tmp_path / "state.json"
    script = "from utils.state_io import state_lock\nimport sys\nwith state_lock(sys.argv[1], timeout=0.1): pass"
    with module.state_lock(path):
        with module.state_lock(path):
            result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True, check=False)
            assert result.returncode != 0
            assert "busy" in result.stderr.lower()
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_state_lock_released_when_owner_process_crashes(tmp_path):
    module = state_io()
    path = tmp_path / "state.json"
    script = "from utils.state_io import state_lock\nimport os, sys\nwith state_lock(sys.argv[1]): os._exit(9)"
    result = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
    assert result.returncode == 9
    with module.state_lock(path, timeout=0.1):
        pass
