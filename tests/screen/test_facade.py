"""Tests for the screen package facade (auto-detection, routing, backward compat)."""

import types

import pytest

import screen as screen_pkg
from screen.backend import ProcessError


class FakeBackend:
    """Minimal stand-in for any ProcessBackend."""

    def __init__(self):
        self.calls = []

    @property
    def backend_name(self):
        return "fake"

    def start(self, name, command, cwd=None):
        self.calls.append(("start", name, command, cwd))

    def send_input(self, name, text):
        self.calls.append(("send_input", name, text))

    def send_raw(self, name, command):
        self.calls.append(("send_raw", name, command))

    def kill(self, name):
        self.calls.append(("kill", name))

    def is_running(self, name):
        self.calls.append(("is_running", name))
        return True

    def connect(self, name):
        self.calls.append(("connect", name))

    def list_sessions(self):
        self.calls.append(("list_sessions",))
        yield "srv1"

    def logpath(self, name):
        self.calls.append(("logpath", name))
        return "/logs/Tag#" + name + ".log"


@pytest.fixture()
def fake_backend(monkeypatch):
    """Inject a FakeBackend as the active backend."""
    fb = FakeBackend()
    monkeypatch.setattr(screen_pkg, "_backend", fb)
    yield fb
    monkeypatch.setattr(screen_pkg, "_backend", None)


# ── backward-compatible alias ───────────────────────────────────────────────


def test_screen_error_is_process_error():
    assert screen_pkg.ScreenError is ProcessError


# ── routing tests ───────────────────────────────────────────────────────────


def test_start_screen_routes_to_backend(fake_backend):
    screen_pkg.start_screen("srv", ["./run"], cwd="/app")
    assert fake_backend.calls == [("start", "srv", ["./run"], "/app")]


def test_send_to_server_routes_to_send_input(fake_backend):
    screen_pkg.send_to_server("srv", "hello")
    assert fake_backend.calls == [("send_input", "srv", "hello")]


def test_send_to_screen_quit_routes_to_kill(fake_backend):
    screen_pkg.send_to_screen("srv", ["quit"])
    assert fake_backend.calls == [("kill", "srv")]


def test_send_to_screen_raw_routes_to_send_raw(fake_backend):
    screen_pkg.send_to_screen("srv", ["select", "."])
    assert fake_backend.calls == [("send_raw", "srv", ["select", "."])]


def test_check_screen_exists_routes_to_is_running(fake_backend):
    assert screen_pkg.check_screen_exists("srv") is True
    assert fake_backend.calls == [("is_running", "srv")]


def test_connect_to_screen_routes_to_connect(fake_backend):
    screen_pkg.connect_to_screen("srv")
    assert fake_backend.calls == [("connect", "srv")]


def test_list_all_screens_routes_to_list_sessions(fake_backend):
    assert list(screen_pkg.list_all_screens()) == ["srv1"]
    assert fake_backend.calls == [("list_sessions",)]


def test_logpath_routes_to_backend(fake_backend):
    assert screen_pkg.logpath("srv") == "/logs/Tag#srv.log"
    assert fake_backend.calls == [("logpath", "srv")]


# ── detection logic ─────────────────────────────────────────────────────────


def test_detect_backend_prefers_screen(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "screen" else None)
    assert screen_pkg._detect_backend() == "screen"


def test_detect_backend_falls_back_to_tmux(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/tmux" if cmd == "tmux" else None)
    assert screen_pkg._detect_backend() == "tmux"


def test_detect_backend_falls_back_to_subprocess(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    assert screen_pkg._detect_backend() == "subprocess"


# ── get_backend accessor ───────────────────────────────────────────────────


def test_get_backend_returns_active(fake_backend):
    assert screen_pkg.get_backend() is fake_backend


# ── __all__ exports ─────────────────────────────────────────────────────────


def test_all_contains_expected_names():
    expected = {
        "ScreenError", "ProcessError",
        "start_screen", "send_to_screen", "send_to_server",
        "check_screen_exists", "connect_to_screen", "list_all_screens",
        "logpath", "get_backend",
    }
    assert expected.issubset(set(screen_pkg.__all__))
