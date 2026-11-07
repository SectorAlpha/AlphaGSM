"""Focused Quake 2 pak mod tests."""

from __future__ import annotations

import shutil
import sys
from unittest.mock import MagicMock, patch
import zipfile

import pytest


sys.modules.pop("gamemodules.q2server", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.archive_install": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
    },
):
    import gamemodules.q2server as mod
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
        self.name = "q2mods"
        self.data = DummyData({"dir": str(server_dir), "gamedir": "baseq2"})


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


def test_q2_mod_state_seeds_defaults(tmp_path):
    server = DummyServer(tmp_path / "server")

    mods = mod.ensure_mod_state(server)

    assert mods["enabled"] is True
    assert mods["autoapply"] is True
    assert mods["desired"] == {"url": []}
    assert mods["installed"] == []


def test_q2_mod_add_url_records_desired_state(tmp_path):
    server = DummyServer(tmp_path / "server")

    mod.q2_mod_command(
        server,
        "add",
        "url",
        "https://example.com/pak1.pak",
    )

    assert server.data["mods"]["desired"]["url"][0]["filename"] == "pak1.pak"
    assert server.data["mods"]["desired"]["url"][0]["archive_type"] == "pak"


def test_q2_mod_apply_installs_archive_content_into_active_gamedir(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    server.data["gamedir"] = "custom"
    archive_path = tmp_path / "payload.zip"
    _write_zip(
        archive_path,
        {
            "custom/pak1.pak": "pak-data",
            "README.txt": "ignored",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.q2_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.q2_mod_command(server, "apply")

    assert (server_root / "custom" / "pak1.pak").read_text() == "pak-data"
    assert server.data["mods"]["last_apply"] == "success"
    assert "custom" in server.data["backupfiles"]
    assert "custom" in server.data["backup"]["profiles"]["default"]["targets"]


def test_q2_mod_apply_installs_bare_pak_archive_into_default_gamedir(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "maps.zip"
    _write_zip(
        archive_path,
        {
            "pak2.pak": "pak-data",
        },
    )
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.q2_mod_command(server, "add", "url", "https://example.com/maps.zip")
    mod.q2_mod_command(server, "apply")

    assert (server_root / "baseq2" / "pak2.pak").read_text() == "pak-data"


def test_q2_mod_apply_rejects_non_pak_archive(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "bad.zip"
    _write_zip(archive_path, {"baseq2/readme.txt": "bad"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.q2_mod_command(server, "add", "url", "https://example.com/bad.zip")

    with pytest.raises(ServerError):
        mod.q2_mod_command(server, "apply")

    assert server.data["mods"]["errors"]
    assert not (server_root / "baseq2" / "readme.txt").exists()


def test_q2_mod_cleanup_removes_only_owned_files(tmp_path, monkeypatch):
    server_root = tmp_path / "server"
    server_root.mkdir()
    server = DummyServer(server_root)
    archive_path = tmp_path / "payload.zip"
    _write_zip(archive_path, {"baseq2/pak-owned.pak": "owned"})
    monkeypatch.setattr(mod._main, "download_to_cache", _fake_download_factory(archive_path))

    mod.q2_mod_command(server, "add", "url", "https://example.com/payload.zip")
    mod.q2_mod_command(server, "apply")
    unmanaged_path = server_root / "baseq2" / "pak-unmanaged.pak"
    unmanaged_path.parent.mkdir(parents=True, exist_ok=True)
    unmanaged_path.write_text("keep")

    mod.q2_mod_command(server, "cleanup")

    assert not (server_root / "baseq2" / "pak-owned.pak").exists()
    assert unmanaged_path.read_text() == "keep"
    assert server.data["mods"]["desired"] == {"url": []}
    assert server.data["mods"]["installed"] == []