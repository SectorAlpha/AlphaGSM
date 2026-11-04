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


@pytest.mark.parametrize("use_archive_installer", [False, True])
def test_exact_relative_file_exclusions_preserve_other_content(
    tmp_path, monkeypatch, use_archive_installer
):
    source = tmp_path / "source"
    payload = {
        "Robust.Server": "dedicated engine",
        "client.bin": "client",
        "base/client.bin": "nested client",
        "other/client.bin": "keep same basename elsewhere",
        "base/server.bin": "server game code",
        "base/maps/one.bsp": "first map",
        "base/maps/two.bsp": "second map",
    }
    for relative_path, content in payload.items():
        path = source / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / "operator.cfg").write_text("operator settings")
    (install_dir / "client.bin").write_text("existing operator file")
    exclusions = ("client.bin", "base/client.bin", "base")

    if use_archive_installer:
        server = DummyServer(install_dir)
        monkeypatch.setattr(
            archive_install.downloader, "getpath", lambda module, args: str(source)
        )
        archive_install.install_archive(server, "zip", skip_relative_files=exclusions)
    else:
        archive_install.sync_tree(source, install_dir, skip_relative_files=exclusions)

    assert (install_dir / "client.bin").read_text() == "existing operator file"
    assert not (install_dir / "base/client.bin").exists()
    assert (install_dir / "operator.cfg").read_text() == "operator settings"
    for relative_path, content in payload.items():
        assert (source / relative_path).read_text() == content
        if relative_path not in exclusions:
            assert (install_dir / relative_path).read_text() == content


def test_sync_tree_copies_complete_payload_by_default(tmp_path):
    source = tmp_path / "source"
    (source / "base").mkdir(parents=True)
    (source / "client.bin").write_text("client")
    (source / "base/client.bin").write_text("nested client")
    install_dir = tmp_path / "install"

    archive_install.sync_tree(source, install_dir)

    assert (install_dir / "client.bin").read_text() == "client"
    assert (install_dir / "base/client.bin").read_text() == "nested client"
