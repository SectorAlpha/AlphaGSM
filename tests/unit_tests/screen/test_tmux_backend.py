"""Tests for TmuxBackend."""

import subprocess as sp

import pytest

from screen.tmux_backend import TmuxBackend
from screen.backend import ProcessError


def _make_backend(tmp_path):
    logdir = tmp_path / "logs"
    logdir.mkdir(exist_ok=True)
    return TmuxBackend("Alpha#", str(logdir), 5)


def test_backend_name():
    assert TmuxBackend("X#", "/tmp", 5).backend_name == "tmux"


def test_start_invokes_tmux_new_session(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, **kw: calls.append(cmd) or b"ok",
    )
    backend.start("srv1", ["./run.sh"], cwd="/srv")
    cmd = calls[0]
    assert cmd[:5] == ["tmux", "new-session", "-d", "-s", "Alpha#srv1"]
    assert "-c" in cmd
    assert "/srv" in cmd
    # Second call should be pipe-pane for logging
    assert "pipe-pane" in calls[1]


def test_start_wraps_called_process_error(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, **kw: (_ for _ in ()).throw(
            sp.CalledProcessError(1, cmd, output=b"err")
        ),
    )
    with pytest.raises(ProcessError, match="tmux new-session failed"):
        backend.start("srv1", ["./run.sh"])


def test_send_raw_raises(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="send_raw is not supported"):
        backend.send_raw("srv1", ["anything"])


def test_send_input_literal_text(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: calls.append(cmd) or b"ok",
    )
    backend.send_input("srv1", "stop\n")
    # Should send literal text then Enter
    assert calls[0] == ["tmux", "send-keys", "-t", "Alpha#srv1", "-l", "stop"]
    assert calls[1] == ["tmux", "send-keys", "-t", "Alpha#srv1", "Enter"]


def test_send_input_ctrl_c(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: calls.append(cmd) or b"ok",
    )
    backend.send_input("srv1", "\003")
    assert calls == [["tmux", "send-keys", "-t", "Alpha#srv1", "C-c"]]


def test_send_input_bare_newline(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: calls.append(cmd) or b"ok",
    )
    backend.send_input("srv1", "\n")
    assert calls == [["tmux", "send-keys", "-t", "Alpha#srv1", "Enter"]]


def test_kill_invokes_kill_session(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: calls.append(cmd) or b"ok",
    )
    backend.kill("srv1")
    assert calls == [["tmux", "kill-session", "-t", "Alpha#srv1"]]


def test_is_running_true(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: b"ok",
    )
    assert backend.is_running("srv1") is True


def test_is_running_false(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell: (_ for _ in ()).throw(
            sp.CalledProcessError(1, cmd, output=b"")
        ),
    )
    assert backend.is_running("srv1") is False


def test_connect_invokes_attach(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    calls = []
    monkeypatch.setattr(sp, "check_call", lambda cmd, shell: calls.append(cmd))
    backend.connect("srv1")
    assert calls == [["tmux", "attach-session", "-t", "Alpha#srv1"]]


def test_list_sessions_filters_by_tag(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, text: "Alpha#one\nAlpha#two\nOther#three\n",
    )
    assert list(backend.list_sessions()) == ["one", "two"]


def test_list_sessions_returns_empty_on_error(tmp_path, monkeypatch):
    backend = _make_backend(tmp_path)
    monkeypatch.setattr(
        sp, "check_output",
        lambda cmd, stderr, shell, text: (_ for _ in ()).throw(
            sp.CalledProcessError(1, cmd, output=b"")
        ),
    )
    assert list(backend.list_sessions()) == []
