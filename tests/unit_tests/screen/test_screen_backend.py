"""Tests for ScreenBackend."""

import os
import subprocess as sp

import pytest

from screen.screen_backend import ScreenBackend
from screen.backend import ProcessError


def _make_backend(tmp_path):
    logdir = tmp_path / "logs"
    logdir.mkdir(exist_ok=True)
    screenrc = str(tmp_path / "alphagsm" / "screenrc")
    template_dir = str(tmp_path / "templates")
    os.makedirs(template_dir, exist_ok=True)
    (tmp_path / "templates" / "screenrc_template.txt").write_text("logfile %s%%S.log\n")
    return ScreenBackend("Alpha#", str(logdir), 5, screenrc, template_dir)


def test_backend_name():
    b = ScreenBackend("X#", "/tmp", 5, "/tmp/rc", "/tmp")
    assert b.backend_name == "screen"


def test_write_screenrc_creates_file(tmp_path):
    backend = _make_backend(tmp_path)
    backend._write_screenrc()
    rc_path = tmp_path / "alphagsm" / "screenrc"
    assert rc_path.exists()
    content = rc_path.read_text()
    assert str(tmp_path / "logs") in content


def test_write_screenrc_no_overwrite_without_force(tmp_path):
    backend = _make_backend(tmp_path)
    backend._write_screenrc()
    rc_path = tmp_path / "alphagsm" / "screenrc"
    rc_path.write_text("custom")
    backend._write_screenrc()
    assert rc_path.read_text() == "custom"


def test_write_screenrc_force_overwrites(tmp_path):
    backend = _make_backend(tmp_path)
    backend._write_screenrc()
    rc_path = tmp_path / "alphagsm" / "screenrc"
    rc_path.write_text("custom")
    backend._write_screenrc(force=True)
    assert rc_path.read_text() != "custom"


def test_start_invokes_screen(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, **kw: calls.append((cmd, kw)) or b"ok",
    )
    result = backend.start("srv1", ["./run.sh"], cwd="/srv")
    assert result == b"ok"
    assert calls[0][0][:3] == ["screen", "-dmLS", "Alpha#srv1"]
    assert calls[0][1] == {"cwd": "/srv"}


def test_start_wraps_file_not_found(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, **kw: (_ for _ in ()).throw(
            FileNotFoundError("bad")
        ),
    )
    with pytest.raises(ProcessError, match="Can't change to directory"):
        backend.start("srv1", ["./run.sh"], cwd="/bad")


def test_send_raw_invokes_screen(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: calls.append(cmd) or b"ok",
    )
    backend.send_raw("srv1", ["select", "."])
    assert calls[0] == [
        "screen", "-S", "Alpha#srv1", "-p", "0", "-X", "select", ".",
    ]


def test_send_input_delegates_to_send_raw(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    calls = []
    monkeypatch.setattr(backend, "send_raw", lambda n, c: calls.append((n, c)))
    backend.send_input("srv1", "hello")
    assert calls == [("srv1", ["stuff", "hello"])]


def test_kill_delegates_to_send_raw(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    calls = []
    monkeypatch.setattr(backend, "send_raw", lambda n, c: calls.append((n, c)))
    backend.kill("srv1")
    assert calls == [("srv1", ["quit"])]


def test_is_running_true_on_success(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    monkeypatch.setattr(backend, "send_raw", lambda n, c: b"ok")
    assert backend.is_running("srv1") is True


def test_is_running_false_on_error(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    monkeypatch.setattr(
        backend, "send_raw",
        lambda n, c: (_ for _ in ()).throw(ProcessError("nope")),
    )
    assert backend.is_running("srv1") is False


def test_connect_invokes_script(monkeypatch):
    backend = ScreenBackend("Alpha#", "/tmp", 5, "/tmp/rc", "/tmp")
    calls = []
    monkeypatch.setattr(sp, "check_call", lambda cmd, shell: calls.append(cmd))
    backend.connect("srv1")
    assert calls[0] == [
        "script", "/dev/null", "-c", "screen -rS 'Alpha#srv1'",
    ]
