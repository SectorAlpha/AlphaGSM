"""Tests for CS2 mod desired-state commands and apply helpers."""

from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch
import zipfile

import pytest

sys_modules_patch = {
    "downloader": MagicMock(),
    "screen": MagicMock(),
    "utils.backups": MagicMock(),
    "utils.backups.backups": MagicMock(),
    "utils.fileutils": MagicMock(),
}

with patch.dict("sys.modules", sys_modules_patch):
    import gamemodules.counterstrike2 as mod


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="cs2mods"):
        self.name = name
        self.data = DummyData()


def test_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer()

    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["gamebanana"] == []
    assert server.data["mods"]["desired"]["workshop"] == []


def test_mod_add_gamebanana_resolves_and_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    monkeypatch.setattr(
        mod,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "file_id": "777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "cs2mod.zip",
        },
    )

    mod.command_functions["mod"](server, "add", "gamebanana", "12345")

    entry = server.data["mods"]["desired"]["gamebanana"][0]
    assert entry["requested_id"] == "12345"
    assert entry["resolved_id"] == "gamebanana.12345.777"


def test_mod_add_workshop_accepts_numeric_id_only(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    mod.command_functions["mod"](server, "add", "workshop", "1234567890")

    assert server.data["mods"]["desired"]["workshop"][0]["workshop_id"] == "1234567890"
    assert server.data["mods"]["desired"]["workshop"][0]["resolved_id"] == "workshop.1234567890"

    with pytest.raises(mod.ServerError, match="numeric workshop id"):
        mod.command_functions["mod"](server, "add", "workshop", "map_bad")


def test_mod_apply_installs_gamebanana_zip_entry(tmp_path, monkeypatch):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "game" / "csgo" / "addons" / "metamod"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.vdf").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "cs2mod.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "plugin.vdf", "game/csgo/addons/metamod/plugin.vdf")

    monkeypatch.setattr(
        mod,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "file_id": "777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "cs2mod.zip",
        },
    )
    monkeypatch.setattr(
        mod,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    mod.command_functions["mod"](server, "add", "gamebanana", "12345")
    mod.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "game" / "csgo" / "addons" / "metamod" / "plugin.vdf"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "gamebanana.12345.777"


def test_mod_apply_installs_workshop_entry_from_downloaded_item(tmp_path, monkeypatch):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    workshop_root = tmp_path / "workshop-cache" / "steamapps" / "workshop" / "content" / "730" / "1234567890"
    payload = workshop_root / "game" / "csgo" / "addons" / "sourcemod"
    payload.mkdir(parents=True)
    (payload / "from_workshop.vdf").write_text("plugin", encoding="utf-8")
    monkeypatch.setattr(
        mod.steamcmd,
        "download_workshop_item",
        lambda path, workshop_app_id, workshop_item_id, steam_anonymous_login_possible: str(
            workshop_root
        ),
    )

    mod.command_functions["mod"](server, "add", "workshop", "1234567890")
    mod.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "game" / "csgo" / "addons" / "sourcemod" / "from_workshop.vdf"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "workshop.1234567890"


def test_mod_cleanup_removes_only_files_recorded_per_mod(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))

    first_owned = (
        Path(server.data["dir"]) / "game" / "csgo" / "addons" / "metamod" / "first.vdf"
    )
    second_owned = (
        Path(server.data["dir"]) / "game" / "csgo" / "cfg" / "second.cfg"
    )
    unowned_file = (
        Path(server.data["dir"]) / "game" / "csgo" / "addons" / "metamod" / "manual.vdf"
    )

    first_owned.parent.mkdir(parents=True)
    second_owned.parent.mkdir(parents=True)
    first_owned.write_text("first", encoding="utf-8")
    second_owned.write_text("second", encoding="utf-8")
    unowned_file.write_text("manual", encoding="utf-8")

    server.data["mods"]["installed"] = [
        {
            "source_type": "gamebanana",
            "resolved_id": "gamebanana.12345.777",
            "installed_files": ["game/csgo/addons/metamod/first.vdf"],
        },
        {
            "source_type": "workshop",
            "resolved_id": "workshop.1234567890",
            "installed_files": ["game/csgo/cfg/second.cfg"],
        },
    ]

    mod.command_functions["mod"](server, "cleanup")

    assert not first_owned.exists()
    assert not second_owned.exists()
    assert unowned_file.exists()