import importlib
import os
import sys

import pytest


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

    with pytest.raises(NameError, match="Path"):
        downloader_module.getpath("url", ("http://example.com/file",))


def test_getpaths_without_module_uses_default_filter(downloader_module):
    with open(downloader_module.DB_PATH, "w") as handle:
        handle.write("url http%3A//example.com/file,server.jar /downloads/a 1.0 1\n")

    with pytest.raises(NameError, match="kwargs"):
        downloader_module.getpaths(None, active=True)
