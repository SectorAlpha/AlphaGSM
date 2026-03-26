"""Tests for the ProcessBackend abstract base class."""

import os

import pytest

from screen.backend import ProcessBackend, ProcessError


class ConcreteBackend(ProcessBackend):
    """Minimal concrete subclass for testing shared helpers."""

    @property
    def backend_name(self):
        return "test"

    def start(self, name, command, cwd=None):
        pass

    def send_input(self, name, text):
        pass

    def send_raw(self, name, command):
        pass

    def kill(self, name):
        pass

    def is_running(self, name):
        return False

    def connect(self, name):
        pass

    def list_sessions(self):
        yield from ()


def _make_backend(tmp_path, keeplogs=5):
    return ConcreteBackend("Tag#", str(tmp_path / "logs"), keeplogs)


def test_process_error_is_exception():
    assert issubclass(ProcessError, Exception)


def test_logpath_joins_components(tmp_path):
    backend = _make_backend(tmp_path)
    assert backend.logpath("srv") == os.path.join(str(tmp_path / "logs"), "Tag#srv.log")


def test_ensure_log_dir_creates_directory(tmp_path):
    backend = _make_backend(tmp_path)
    backend._ensure_log_dir()
    assert os.path.isdir(str(tmp_path / "logs"))


def test_rotatelogs_noop_when_no_log(tmp_path):
    backend = _make_backend(tmp_path)
    backend._ensure_log_dir()
    backend._rotatelogs("srv")  # should not raise


def test_rotatelogs_renames_current_and_shifts(tmp_path):
    backend = _make_backend(tmp_path, keeplogs=3)
    logdir = tmp_path / "logs"
    logdir.mkdir()
    (logdir / "Tag#srv.log").write_text("current")
    (logdir / "Tag#srv.log.0").write_text("old0")
    (logdir / "Tag#srv.log.1").write_text("old1")

    backend._rotatelogs("srv")

    assert not (logdir / "Tag#srv.log").exists()
    assert (logdir / "Tag#srv.log.0").read_text() == "current"
    assert (logdir / "Tag#srv.log.1").read_text() == "old0"
    assert (logdir / "Tag#srv.log.2").read_text() == "old1"


def test_rotatelogs_drops_old_logs_beyond_keeplogs(tmp_path):
    backend = _make_backend(tmp_path, keeplogs=2)
    logdir = tmp_path / "logs"
    logdir.mkdir()
    (logdir / "Tag#srv.log").write_text("current")
    (logdir / "Tag#srv.log.0").write_text("old0")
    (logdir / "Tag#srv.log.1").write_text("old1")

    backend._rotatelogs("srv")

    assert (logdir / "Tag#srv.log.0").read_text() == "current"
    assert (logdir / "Tag#srv.log.1").read_text() == "old0"
    assert not (logdir / "Tag#srv.log.2").exists()


def test_cannot_instantiate_abstract_backend_directly():
    with pytest.raises(TypeError):
        ProcessBackend("Tag#", "/tmp/logs", 5)
