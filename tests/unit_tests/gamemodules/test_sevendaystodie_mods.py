"""Focused 7 Days to Die modlet tests."""

from __future__ import annotations

import shutil
import sys
from unittest.mock import MagicMock, patch
import zipfile

import pytest


sys.modules.pop("gamemodules.sevendaystodie", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.sevendaystodie as mod
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
        self.name = "sevendaymods"
        self.data = DummyData({"dir": str(server_dir)})


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


def test_sevenday_mod_state_seeds_defaults(tmp_path):
    server = DummyServer(tmp_path / "server")

    mods = mod.ensure_mod_state(server)

    assert mods["enabled"] is True
    assert mods["autoapply"] is True
    assert mods["desired"] == {"url": []}
    assert mods["installed"] == []


def test_sevenday_mod_add_url_records_desired_state(tmp_path):
    server = DummyServer(tmp_path / "server")

    mod.sevenday_mod_command(
        server,
        "add",
        "url",
        "https://example.com/servertools.zip",
    )

    assert server.data["mods"]["desired"]["url"][0]["filename"] == "servertools.zip"
    assert server.data["mods"]["desired"]["url"][0]["archive_type"] == "zip"


def test_sevenday_mod_apply_installs_prefixed_mods_archive(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "payload.zip"
    _write_zip(
        archive_path,
        {
            "Mods/ServerTools/ModInfo.xml": "<xml/>",
            "Mods/ServerTools/Config/config.xml": "cfg",
            "README.txt": "ignored",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.sevenday_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.sevenday_mod_command(server, "apply")

    assert (server_root / "Mods" / "ServerTools" / "ModInfo.xml").read_text() == "<xml/>"
    assert (server_root / "Mods" / "ServerTools" / "Config" / "config.xml").read_text() == "cfg"
    assert server.data["mods"]["last_apply"] == "success"
    assert server.data["mods"]["errors"] == []


def test_sevenday_mod_apply_installs_top_level_modlet_archive(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "simplemod.zip"
    _write_zip(
        archive_path,
        {
            "ModInfo.xml": "<xml/>",
            "Config/settings.xml": "cfg",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.sevenday_mod_command(server, "add", "url", "https://example.com/simplemod.zip")
    mod.sevenday_mod_command(server, "apply")

    assert (server_root / "Mods" / "simplemod" / "ModInfo.xml").read_text() == "<xml/>"
    assert (server_root / "Mods" / "simplemod" / "Config" / "settings.xml").read_text() == "cfg"


def test_sevenday_mod_apply_rejects_archive_without_modinfo(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "bad.zip"
    _write_zip(archive_path, {"ServerTools/Config/config.xml": "cfg"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.sevenday_mod_command(server, "add", "url", "https://example.com/bad.zip")

    with pytest.raises(ServerError):
        mod.sevenday_mod_command(server, "apply")

    assert server.data["mods"]["errors"]
    assert not (server_root / "Mods" / "ServerTools").exists()


def test_sevenday_mod_cleanup_removes_only_owned_files(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "payload.zip"
    _write_zip(archive_path, {"Mods/OwnedMod/ModInfo.xml": "<xml/>"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.sevenday_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.sevenday_mod_command(server, "apply")
    unmanaged_path = server_root / "Mods" / "SharedMod" / "ModInfo.xml"
    unmanaged_path.parent.mkdir(parents=True, exist_ok=True)
    unmanaged_path.write_text("<keep/>")

    mod.sevenday_mod_command(server, "cleanup")

    assert not (server_root / "Mods" / "OwnedMod").exists()
    assert unmanaged_path.read_text() == "<keep/>"
    assert server.data["mods"]["desired"] == {"url": []}
    assert server.data["mods"]["installed"] == []