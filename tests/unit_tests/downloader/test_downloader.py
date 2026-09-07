import importlib
import os
import sys

import pytest


def test_import_accepts_unmapped_posix_uid(monkeypatch):
    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", "./tests/alphagsm-test.conf")
    monkeypatch.setattr(
        "pwd.getpwuid",
        lambda _uid: (_ for _ in ()).throw(KeyError("uid is not in passwd")),
    )
    sys.modules.pop("downloader.downloader", None)
    sys.modules.pop("downloader", None)

    module = importlib.import_module("downloader.downloader")

    assert module.USER is None


@pytest.fixture
def downloader_module(monkeypatch, tmp_path):
    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", "./tests/alphagsm-test.conf")
    sys.modules.pop("downloader.downloader", None)
    sys.modules.pop("downloader", None)
    module = importlib.import_module("downloader.downloader")
    module.DB_PATH = str(tmp_path / "downloads.txt")
    module.LOCK_PATH = module.DB_PATH + module.LOCK_SUFFIX
    module.UPDATE_PATH = module.DB_PATH + module.UPDATE_SUFFIX
    module.TARGET_PATH = str(tmp_path / "store")
    module.PARENTLEN = 1
    module.PARENTCHARS = "a"
    module.DIRLEN = 3
    module.DIRCHARS = "b"
    module.MAX_TRIES = 3
    module.RETRYPARENT = 1
    return module


def test_expandcustomuser_expands_tilde_for_requested_user(downloader_module, monkeypatch):
    fake_pwd = type("Pwd", (), {"pw_dir": "/srv/tester"})()
    monkeypatch.setattr(downloader_module.pwd, "getpwnam", lambda user: fake_pwd)

    assert downloader_module.expandcustomuser("~/downloads", "tester") == "/srv/tester/downloads"
    assert downloader_module.expandcustomuser("/var/data", "tester") == "/var/data"


def test_generatepath_creates_parent_and_child_directory(downloader_module):
    path = downloader_module.generatepath()

    assert path is not None
    assert os.path.isdir(path)
    assert path.startswith(downloader_module.TARGET_PATH)


def test_getpathifexists_bootstraps_missing_database(downloader_module):
    result = downloader_module.getpathifexists("url", ("http://example.com/file", "server.jar"))

    assert result is None
    assert os.path.isfile(downloader_module.DB_PATH)


def test_getpathifexists_returns_matching_active_entry(downloader_module):
    os.makedirs(os.path.dirname(downloader_module.DB_PATH), exist_ok=True)
    with open(downloader_module.DB_PATH, "w") as handle:
        handle.write("url http%3A//example.com/file,server.jar /downloads/a 1234.0 1\n")
        handle.write("url http%3A//example.com/other,server.jar /downloads/b 1235.0 0\n")

    result = downloader_module.getpathifexists("url", ("http://example.com/file", "server.jar"))

    assert result == "/downloads/a"


def test_getargsforpath_decodes_database_arguments(downloader_module):
    os.makedirs(os.path.dirname(downloader_module.DB_PATH), exist_ok=True)
    with open(downloader_module.DB_PATH, "w") as handle:
        handle.write("url http%3A//example.com/file,server.jar /downloads/a 1234.0 1\n")

    assert downloader_module.getargsforpath("/downloads/a") == ("url", ["http://example.com/file", "server.jar"])
    assert downloader_module.getargsforpath("/downloads/missing") is None


def test_download_delegates_to_module_and_returns_generated_path(downloader_module, monkeypatch):
    called = {}

    class FakeModule:
        @staticmethod
        def download(path, args):
            called["path"] = path
            called["args"] = args

    monkeypatch.setattr(downloader_module, "generatepath", lambda: "/downloads/new")
    monkeypatch.setattr(downloader_module, "_findmodule", lambda name: FakeModule)

    result = downloader_module.download("url", ("http://example.com/file", "server.jar"))

    assert result == "/downloads/new"
    assert called == {"path": "/downloads/new", "args": ("http://example.com/file", "server.jar")}


def test_download_raises_when_no_storage_path_can_be_generated(downloader_module, monkeypatch):
    monkeypatch.setattr(downloader_module, "generatepath", lambda: None)

    with pytest.raises(downloader_module.DownloaderError, match="Can't generate storage path"):
        downloader_module.download("url", ("a",))


def test_getpath_returns_existing_database_hit_without_downloading(downloader_module, monkeypatch):
    monkeypatch.setattr(downloader_module, "getpathifexists", lambda module, args: "/downloads/existing")

    assert downloader_module.getpath("url", ("http://example.com/file",)) == "/downloads/existing"


def test_getpath_rechecks_database_after_lock_before_downloading(downloader_module, monkeypatch):
    calls = {"count": 0}

    def fake_getpathifexists(module, args):
        calls["count"] += 1
        return None if calls["count"] == 1 else "/downloads/existing"

    monkeypatch.setattr(downloader_module, "getpathifexists", fake_getpathifexists)
    monkeypatch.setattr(downloader_module.os, "getuid", lambda: downloader_module.pwd.getpwnam(downloader_module.USER).pw_uid)

    assert downloader_module.getpath("url", ("http://example.com/file",)) == "/downloads/existing"
    assert not os.path.exists(downloader_module.LOCK_PATH)


def test_getpaths_without_module_uses_default_filter(downloader_module):
    with open(downloader_module.DB_PATH, "w") as handle:
        handle.write("url http%3A//example.com/file,server.jar /downloads/a 1.0 1\n")

    assert downloader_module.getpaths(None, active=True) == [
        ("url", ["http://example.com/file", "server.jar"], "/downloads/a", "1.0", "1")
    ]


def test_getpaths_filters_active_records_and_sorts_dates_numerically(downloader_module):
    with open(downloader_module.DB_PATH, "w") as handle:
        handle.write("url later /downloads/b 10.0 1\n")
        handle.write("url inactive /downloads/hidden 1.0 0\n")
        handle.write("url earlier /downloads/a 2.0 1\n")
    assert [row[2] for row in downloader_module.getpaths(None, sort="date", active=True)] == [
        "/downloads/a", "/downloads/b"
    ]


def test_getpaths_passes_sort_and_filters_to_module(downloader_module, monkeypatch):
    calls = []
    module = type("Downloader", (), {"getfilter": staticmethod(
        lambda **kwargs: (calls.append(kwargs) or (lambda *_args: True), None)
    )})
    monkeypatch.setattr(downloader_module, "_findmodule", lambda _name: module)
    open(downloader_module.DB_PATH, "w").close()
    assert downloader_module.getpaths("url", sort="date", custom=True) == []
    assert calls == [{"sort": "date", "custom": True}]


@pytest.mark.parametrize("frozen", [False, True])
def test_cross_user_downloader_uses_matching_install_entry(downloader_module, monkeypatch, frozen):
    import subprocess
    from pathlib import Path

    commands = []
    monkeypatch.setattr(downloader_module, "getpathifexists", lambda *_args: None)
    monkeypatch.setattr(downloader_module, "IS_WINDOWS", False)
    monkeypatch.setattr(downloader_module, "USER", "cache-owner")
    monkeypatch.setattr(downloader_module.pwd, "getpwnam", lambda _name: type("User", (), {"pw_uid": 1234})())
    monkeypatch.setattr(downloader_module.os, "getuid", lambda: 4321)
    monkeypatch.setattr(downloader_module.sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(downloader_module.sys, "executable", "/install with spaces/alphagsm")
    monkeypatch.setattr(subprocess, "check_output", lambda command: commands.append(command) or b"/cache/a%20file%2Bdata\n")

    assert downloader_module.getpath("url", ["https://example.invalid/a?x=1&y=2", "server.jar"]) == "/cache/a file+data"
    executable = (["/install with spaces/alphagsm", "--_download"] if frozen else
                  [str(Path(downloader_module.__file__).resolve().parents[2] / "alphagsm-downloads")])
    assert commands == [["sudo", "-Hu", "cache-owner"] + executable + [
        "url", "https://example.invalid/a?x=1&y=2", "server.jar"
    ]]


def test_download_helper_quotes_only_path_on_stdout(downloader_module, monkeypatch, capsys):
    def download(module, args):
        assert module == "url"
        assert args == ["release"]
        print("Downloading release")
        return "/cache/a file+data"

    monkeypatch.setattr(downloader_module, "getpath", download)
    assert downloader_module.run_download_helper(["url", "release"]) == 0
    output = capsys.readouterr()
    assert output.out == "/cache/a%20file%2Bdata\n"
    assert output.err == "Downloading release\n"


def test_download_helper_preserves_downloader_error_status(downloader_module, monkeypatch, capsys):
    def fail(*_args):
        raise downloader_module.DownloaderError("release unavailable", ret=7)

    monkeypatch.setattr(downloader_module, "getpath", fail)
    assert downloader_module.run_download_helper(["url", "release"]) == 7
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "release unavailable\n"


def test_launcher_dispatches_download_helper_without_core(monkeypatch):
    import runpy
    from pathlib import Path
    from types import SimpleNamespace

    calls = []
    monkeypatch.setitem(sys.modules, "downloader", SimpleNamespace(
        run_download_helper=lambda args: calls.append(args) or 7,
    ))
    monkeypatch.setitem(sys.modules, "core", None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "argv", ["alphagsm", "--_download", "url", "release"])
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(str(Path(__file__).resolve().parents[3] / "alphagsm"), run_name="__main__")
    assert caught.value.code == 7
    assert calls == [["url", "release"]]


def test_download_helper_rejects_missing_module(downloader_module, capsys):
    assert downloader_module.run_download_helper([]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "download module is required" in output.err
