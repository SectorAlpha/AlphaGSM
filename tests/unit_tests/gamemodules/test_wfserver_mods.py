"""Focused Warfork pk3 mod tests."""

from __future__ import annotations

import shutil
import sys
from unittest.mock import MagicMock, patch
import zipfile

import pytest


sys.modules.pop("gamemodules.wfserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.wfserver as mod
    from server import ServerError


class DummyData(dict):
    def save(self):
        pass

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    def get(self, key, default=None):
        return super().get(key, default)


class DummyServer:
    def __init__(self, server_dir):
        self.name = "wfmods"
        self.data = DummyData({"dir": str(server_dir), "fs_game": "basewf"})


def _write_zip(archive_path, members):
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as handle:
        for member_name, member_data in members.items():
            handle.writestr(member_name, member_data)


def _fake_download_factory(source_path):
    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        del url, allowed_hosts, checksum
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        return target_path

    return _fake_download


def test_wf_mod_state_seeds_defaults(tmp_path):
    server = DummyServer(tmp_path / "server")

    mods = mod.ensure_mod_state(server)

    assert mods["enabled"] is True
    assert mods["autoapply"] is True
    assert mods["desired"] == {"url": []}
    assert mods["installed"] == []


def test_wf_mod_add_url_records_desired_state(tmp_path):
    server = DummyServer(tmp_path / "server")

    mod.wf_mod_command(
        server,
        "add",
        "url",
        "https://example.com/map.pk3",
    )

    assert server.data["mods"]["desired"]["url"][0]["filename"] == "map.pk3"
    assert server.data["mods"]["desired"]["url"][0]["archive_type"] == "pk3"


def test_wf_mod_apply_installs_archive_content_into_active_fs_game(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    server.data["fs_game"] = "duelmod"
    archive_path = tmp_path / "payload.zip"
    _write_zip(
        archive_path,
        {
            "duelmod/mappack.pk3": "pk3-data",
            "README.txt": "ignored",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.wf_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.wf_mod_command(server, "apply")

    assert (server_root / "duelmod" / "mappack.pk3").read_text() == "pk3-data"
    assert server.data["mods"]["last_apply"] == "success"
    assert "duelmod" in server.data["backupfiles"]
    assert "duelmod" in server.data["backup"]["profiles"]["default"]["targets"]


def test_wf_mod_apply_installs_bare_pk3_archive_into_default_fs_game(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "maps.zip"
    _write_zip(
        archive_path,
        {
            "pak-custom.pk3": "pk3-data",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.wf_mod_command(server, "add", "url", "https://example.com/maps.zip")
    mod.wf_mod_command(server, "apply")

    assert (server_root / "basewf" / "pak-custom.pk3").read_text() == "pk3-data"


def test_wf_mod_apply_rejects_non_pk3_archive(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "bad.zip"
    _write_zip(archive_path, {"basewf/readme.txt": "bad"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.wf_mod_command(server, "add", "url", "https://example.com/bad.zip")

    with pytest.raises(ServerError):
        mod.wf_mod_command(server, "apply")

    assert server.data["mods"]["errors"]
    assert not (server_root / "basewf" / "readme.txt").exists()


def test_wf_mod_cleanup_removes_only_owned_files(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "payload.zip"
    _write_zip(archive_path, {"basewf/pak-owned.pk3": "owned"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.wf_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.wf_mod_command(server, "apply")
    unmanaged_path = server_root / "basewf" / "pak-unmanaged.pk3"
    unmanaged_path.parent.mkdir(parents=True, exist_ok=True)
    unmanaged_path.write_text("keep")

    mod.wf_mod_command(server, "cleanup")

    assert not (server_root / "basewf" / "pak-owned.pk3").exists()
    assert unmanaged_path.read_text() == "keep"
    assert server.data["mods"]["desired"] == {"url": []}
    assert server.data["mods"]["installed"] == []