import os
import subprocess as sp
import sys
import types

import pytest

import screen.screen as screen_module


class FakeSection(dict):
    def getsection(self, key):
        return self[key]


def test_rotatelogs_returns_when_current_log_is_missing(tmp_path):
    screen_module.rotatelogs(str(tmp_path), "server.log")

    assert list(tmp_path.iterdir()) == []


def test_rotatelogs_shifts_existing_logs_and_drops_old_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(screen_module, "KEEPLOGS", 3)
    current = tmp_path / "server.log"
    current.write_text("current")
    (tmp_path / "server.log.0").write_text("old0")
    (tmp_path / "server.log.1").write_text("old1")
    (tmp_path / "server.log.3").write_text("old3")

    screen_module.rotatelogs(str(tmp_path), "server.log")

    assert not (tmp_path / "server.log").exists()
    assert (tmp_path / "server.log.0").read_text() == "current"
    assert (tmp_path / "server.log.1").read_text() == "old0"
    assert not (tmp_path / "server.log.3").exists()


def test_start_screen_creates_log_dir_rotates_logs_and_invokes_screen(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(screen_module, "LOGPATH", str(tmp_path / "logs"))
    monkeypatch.setattr(screen_module, "SCREENRC", str(tmp_path / "screenrc"))
    monkeypatch.setattr(screen_module, "SESSIONTAG", "Alpha#")
    monkeypatch.setattr(screen_module, "write_screenrc", lambda force=False: calls.append(("write_screenrc", force)))
    monkeypatch.setattr(screen_module, "rotatelogs", lambda dirn, name: calls.append(("rotatelogs", dirn, name)))
    monkeypatch.setattr(screen_module.sp, "check_output", lambda cmd, stderr, shell, **kwargs: calls.append(("check_output", cmd, kwargs)) or b"ok")

    result = screen_module.start_screen("server1", ["run", "now"], cwd="/srv/app")

    assert result == b"ok"
    assert os.path.isdir(screen_module.LOGPATH)
    assert calls[0] == ("write_screenrc", False)
    assert calls[1] == ("rotatelogs", screen_module.LOGPATH, "Alpha#server1.log")
    assert calls[2][1] == ["screen", "-dmLS", "Alpha#server1", "-c", screen_module.SCREENRC, "run", "now"]
    assert calls[2][2] == {"cwd": "/srv/app"}


def test_start_screen_wraps_called_process_error(tmp_path, monkeypatch):
    monkeypatch.setattr(screen_module, "LOGPATH", str(tmp_path / "logs"))
    monkeypatch.setattr(screen_module, "write_screenrc", lambda force=False: None)
    monkeypatch.setattr(screen_module, "rotatelogs", lambda dirn, name: None)

    def fake_check_output(cmd, stderr, shell, **kwargs):
        raise sp.CalledProcessError(2, cmd, output=b"boom")

    monkeypatch.setattr(screen_module.sp, "check_output", fake_check_output)

    with pytest.raises(TypeError, match="can only concatenate str"):
        screen_module.start_screen("server1", ["run"])


def test_start_screen_wraps_missing_cwd_error(tmp_path, monkeypatch):
    monkeypatch.setattr(screen_module, "LOGPATH", str(tmp_path / "logs"))
    monkeypatch.setattr(screen_module, "write_screenrc", lambda force=False: None)
    monkeypatch.setattr(screen_module, "rotatelogs", lambda dirn, name: None)
    monkeypatch.setattr(
        screen_module.sp,
        "check_output",
        lambda cmd, stderr, shell, **kwargs: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    with pytest.raises(screen_module.ScreenError, match="Can't change to directory '/missing' while starting screen"):
        screen_module.start_screen("server1", ["run"], cwd="/missing")


def test_send_to_screen_invokes_screen_with_expected_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(screen_module, "SESSIONTAG", "Alpha#")
    monkeypatch.setattr(screen_module.sp, "check_output", lambda cmd, stderr, shell: calls.append(cmd) or b"done")

    result = screen_module.send_to_screen("server1", ["stuff", "say hi"])

    assert result == b"done"
    assert calls == [["screen", "-S", "Alpha#server1", "-p", "0", "-X", "stuff", "say hi"]]


def test_send_to_screen_wraps_called_process_error(monkeypatch):
    monkeypatch.setattr(screen_module.sp, "check_output", lambda cmd, stderr, shell: (_ for _ in ()).throw(sp.CalledProcessError(3, cmd, output=b"bad")))

    with pytest.raises(screen_module.ScreenError, match="Screen failed with return value: 3"):
        screen_module.send_to_screen("server1", ["select", "."])


def test_send_to_server_delegates_to_send_to_screen(monkeypatch):
    calls = []
    monkeypatch.setattr(screen_module, "send_to_screen", lambda name, command: calls.append((name, command)) or "ok")

    result = screen_module.send_to_server("server1", "status")

    assert result == "ok"
    assert calls == [("server1", ["stuff", "status"])]


def test_check_screen_exists_reflects_send_to_screen_result(monkeypatch):
    monkeypatch.setattr(screen_module, "send_to_screen", lambda name, command: b"ok")
    assert screen_module.check_screen_exists("server1") is True

    monkeypatch.setattr(screen_module, "send_to_screen", lambda name, command: (_ for _ in ()).throw(screen_module.ScreenError("nope")))
    assert screen_module.check_screen_exists("server1") is False


def test_connect_to_screen_invokes_script_wrapper(monkeypatch):
    calls = []
    monkeypatch.setattr(screen_module, "SESSIONTAG", "Alpha#")
    monkeypatch.setattr(screen_module.sp, "check_call", lambda cmd, shell: calls.append((cmd, shell)) or 0)

    screen_module.connect_to_screen("server1")

    assert calls == [(["script", "/dev/null", "-c", "screen -rS 'Alpha#server1'"], False)]


def test_connect_to_screen_wraps_called_process_error(monkeypatch):
    monkeypatch.setattr(
        screen_module.sp,
        "check_call",
        lambda cmd, shell: (_ for _ in ()).throw(sp.CalledProcessError(4, cmd)),
    )

    with pytest.raises(screen_module.ScreenError, match="Screen Failed with return value: 4"):
        screen_module.connect_to_screen("server1")


def test_list_all_screens_returns_current_and_other_user_sessions(monkeypatch):
    monkeypatch.setattr(screen_module.os, "getuid", lambda: 123)
    pwd_module = types.ModuleType("pwd")
    pwd_module.getpwuid = lambda uid: ("alice",)
    monkeypatch.setitem(sys.modules, "pwd", pwd_module)
    monkeypatch.setattr(
        screen_module.os,
        "walk",
        lambda root: iter(
            [
                ("/var/run/screen/S-alice", [], ["100.AlphaGSM#one", "200.ignore"]),
                ("/var/run/screen/S-bob", [], ["300.AlphaGSM#two"]),
            ]
        ),
    )

    assert list(screen_module.list_all_screens()) == ["one", "bob/two"]


def test_write_screenrc_creates_file_from_template(tmp_path, monkeypatch):
    root = tmp_path / "alphagsm"
    template = tmp_path / "screenrc_template.txt"
    template.write_text("logfile %s%%S.log\n")
    monkeypatch.setattr(screen_module, "SCREENRC", str(root / "screenrc"))
    monkeypatch.setattr(screen_module, "LOGPATH", str(tmp_path / "logs"))
    monkeypatch.setattr(screen_module.settings, "_user", FakeSection({"core": {"alphagsm_path": str(root)}}))
    monkeypatch.setattr(screen_module.os.path, "dirname", lambda path: str(tmp_path))
    monkeypatch.setattr(screen_module.os.path, "abspath", lambda path: path)

    screen_module.write_screenrc()

    assert (root / "screenrc").read_text() == "logfile " + str(tmp_path / "logs") + "/%S.log\n"


def test_write_screenrc_force_rewrites_existing_file(tmp_path, monkeypatch):
    root = tmp_path / "alphagsm"
    root.mkdir()
    screenrc_path = root / "screenrc"
    screenrc_path.write_text("old")
    template = tmp_path / "screenrc_template.txt"
    template.write_text("new %s\n")
    monkeypatch.setattr(screen_module, "SCREENRC", str(screenrc_path))
    monkeypatch.setattr(screen_module, "LOGPATH", str(tmp_path / "logs"))
    monkeypatch.setattr(screen_module.settings, "_user", FakeSection({"core": {"alphagsm_path": str(root)}}))
    monkeypatch.setattr(screen_module.os.path, "dirname", lambda path: str(tmp_path))
    monkeypatch.setattr(screen_module.os.path, "abspath", lambda path: path)

    screen_module.write_screenrc(force=True)

    assert screenrc_path.read_text() == "new " + str(tmp_path / "logs") + "/\n"


def test_logpath_joins_log_directory_and_session_tag(monkeypatch):
    monkeypatch.setattr(screen_module, "LOGPATH", "/var/log/alphagsm")
    monkeypatch.setattr(screen_module, "SESSIONTAG", "Alpha#")

    assert screen_module.logpath("server1") == "/var/log/alphagsm/Alpha#server1.log"
