"""Windows-style open-reader contention must not interrupt stopped evidence."""

import json
from pathlib import Path
import sys

import pytest

import screen.supervisor as supervisor


def test_endpoint_cleanup_retries_temporary_reader_contention(tmp_path, monkeypatch):
    endpoint = tmp_path / "endpoint.json"
    endpoint.write_text("{}", encoding="utf-8")
    original_unlink = Path.unlink
    attempts = []

    def contended_unlink(path, *args, **kwargs):
        if path == endpoint:
            attempts.append(path)
            if len(attempts) < 3:
                raise PermissionError("endpoint is open in a status reader")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", contended_unlink)
    monkeypatch.setattr(supervisor.time, "sleep", lambda _delay: None)
    supervisor.publish_stopped_state(endpoint)
    assert len(attempts) == 3
    assert not endpoint.exists()
    assert json.loads((tmp_path / "stopped.json").read_text()) == {"stopped": True}


def test_endpoint_cleanup_contention_is_bounded_and_recorded(tmp_path, monkeypatch):
    endpoint = tmp_path / "endpoint.json"
    endpoint.write_text("{}", encoding="utf-8")
    original_unlink = Path.unlink
    delays = []

    def contended_unlink(path, *args, **kwargs):
        if path == endpoint:
            raise PermissionError("endpoint is still open")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", contended_unlink)
    monkeypatch.setattr(supervisor.time, "sleep", delays.append)
    supervisor.publish_stopped_state(endpoint)
    assert endpoint.exists()
    assert 0 < sum(delays) <= 1
    stopped = json.loads((tmp_path / "stopped.json").read_text())
    assert stopped["stopped"] is True
    assert "endpoint is still open" in stopped["endpoint_cleanup_error"]


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows file sharing semantics")
def test_native_windows_endpoint_reader_can_finish_during_cleanup(tmp_path, monkeypatch):
    endpoint = tmp_path / "endpoint.json"
    endpoint.write_text("{}", encoding="utf-8")
    reader = endpoint.open(encoding="utf-8")
    delays = []

    def release_reader(delay):
        delays.append(delay)
        reader.close()

    monkeypatch.setattr(supervisor.time, "sleep", release_reader)
    try:
        supervisor.publish_stopped_state(endpoint)
    finally:
        reader.close()
    assert delays == [0.05]
    assert not endpoint.exists()
    assert json.loads((tmp_path / "stopped.json").read_text()) == {"stopped": True}
