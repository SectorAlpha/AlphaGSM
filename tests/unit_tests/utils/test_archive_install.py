"""Tests for utils.archive_install helpers."""

import pytest

from server import ServerError
from utils import archive_install
from utils.archive_install import detect_compression


class DummyData(dict):
    def save(self):
        self["saved"] = self.get("saved", 0) + 1


class DummyServer:
    def __init__(self, install_dir):
        self.data = DummyData(
            dir=str(install_dir) + "/",
            exe_name="Robust.Server",
            url="https://example.com/SS14.Server_linux-x64.zip",
            download_name="SS14.Server_linux-x64.zip",
        )


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("server.zip", "zip"),
        ("server.tar", "tar"),
        ("server.tar.gz", "tar.gz"),
        ("server.tgz", "tar.gz"),
        ("server.tar.bz2", "tar.bz2"),
        ("server.tbz2", "tar.bz2"),
        ("SERVER.ZIP", "zip"),
        ("server.TAR.GZ", "tar.gz"),
        ("server.7z", "7z"),
        ("SERVER.7Z", "7z"),
    ],
)
def test_detect_compression(filename, expected):
    assert detect_compression(filename) == expected


def test_detect_compression_unknown():
    with pytest.raises(ServerError):
        detect_compression("server.rar")


def test_install_archive_keeps_top_level_files_when_stage_has_single_subdir(
    tmp_path,
    monkeypatch,
):
    stage_root = tmp_path / "stage"
    stage_root.mkdir()
    (stage_root / "SS14.Server_linux-x64.zip").write_text("archive")
    (stage_root / "Robust.Server").write_text("#!/bin/sh\n")
    resources_dir = stage_root / "Resources"
    resources_dir.mkdir()
    (resources_dir / "resource.txt").write_text("payload")

    install_dir = tmp_path / "install"
    server = DummyServer(install_dir)
    monkeypatch.setattr(archive_install.downloader, "getpath", lambda module, args: str(stage_root))

    archive_install.install_archive(server, "zip")

    assert (install_dir / "Robust.Server").is_file()
    assert (install_dir / "Robust.Server").stat().st_mode & 0o111
    assert (install_dir / "Resources" / "resource.txt").is_file()
    assert not (install_dir / "SS14.Server_linux-x64.zip").exists()
    assert server.data["current_url"] == server.data["url"]


def test_install_archive_repairs_execute_bit_for_cached_install(tmp_path, monkeypatch):
    stage_root = tmp_path / "stage"
    stage_root.mkdir()
    (stage_root / "SS14.Server_linux-x64.zip").write_text("archive")
    (stage_root / "Robust.Server").write_text("#!/bin/sh\n")

    install_dir = tmp_path / "install"
    server = DummyServer(install_dir)
    monkeypatch.setattr(archive_install.downloader, "getpath", lambda module, args: str(stage_root))

    archive_install.install_archive(server, "zip")
    exe_path = install_dir / "Robust.Server"
    exe_path.chmod(0o644)

    archive_install.install_archive(server, "zip")

    assert exe_path.stat().st_mode & 0o111
