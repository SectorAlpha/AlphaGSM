from pathlib import Path
import shutil
import sys
from unittest.mock import MagicMock, patch
import zipfile

import pytest


sys.modules.pop("gamemodules.scpslserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.scpslserver as mod


MAIN_MODULE = mod._main


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="scpslmods"):
        self.name = name
        self.data = DummyData()


def _configure_server(server, tmp_path):
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))


def test_scpsl_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer()

    _configure_server(server, tmp_path)

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["url"] == []
    assert server.data["mods"]["desired"]["moddb"] == []


def test_scpsl_mod_add_url_persists_entry(tmp_path):
    server = DummyServer()
    _configure_server(server, tmp_path)

    mod.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/ExamplePlugin.dll",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["requested_id"] == "https://plugins.example.invalid/ExamplePlugin.dll"
    assert entry["filename"] == "ExamplePlugin.dll"
    assert entry["archive_type"] == "dll"


def test_scpsl_checked_in_manifest_resolves_verified_plugin_family(monkeypatch):
    monkeypatch.delenv("ALPHAGSM_SCPSL_CURATED_MODS_PATH", raising=False)

    resolved = mod.load_scpsl_curated_registry().resolve("betterhelpcommand")

    assert resolved.resolved_id == "betterhelpcommand.1.0.0"
    assert resolved.archive_type == "dll"
    assert list(resolved.hosts) == ["github.com"]
    assert resolved.url.endswith("/BetterHelpCommand_LabAPI.dll")
    assert list(resolved.destinations) == ["plugins/global"]


def test_scpsl_checked_in_manifest_resolves_escapeplan_family(monkeypatch):
    monkeypatch.delenv("ALPHAGSM_SCPSL_CURATED_MODS_PATH", raising=False)

    resolved = mod.load_scpsl_curated_registry().resolve("escapeplan")

    assert resolved.resolved_id == "escapeplan.3.0"
    assert resolved.archive_type == "dll"
    assert list(resolved.hosts) == ["github.com"]
    assert resolved.url.endswith("/EscapePlan.dll")
    assert list(resolved.destinations) == ["plugins/global"]


def test_scpsl_checked_in_manifest_resolves_respawntimer_family(monkeypatch):
    monkeypatch.delenv("ALPHAGSM_SCPSL_CURATED_MODS_PATH", raising=False)

    resolved = mod.load_scpsl_curated_registry().resolve("respawntimer")

    assert resolved.resolved_id == "respawntimer.1.3.0"
    assert resolved.archive_type == "dll"
    assert list(resolved.hosts) == ["github.com"]
    assert resolved.url.endswith("/RespawnTimer.dll")
    assert list(resolved.destinations) == ["plugins/global"]


def test_scpsl_mod_add_manifest_persists_entry(tmp_path):
    server = DummyServer()
    _configure_server(server, tmp_path)

    mod.command_functions["mod"](server, "add", "manifest", "betterhelpcommand")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "betterhelpcommand"
    assert entry["resolved_id"] == "betterhelpcommand.1.0.0"


def test_scpsl_mod_apply_installs_plugin_dll(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")
    plugin_dll = tmp_path / "ExamplePlugin.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        MAIN_MODULE,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    mod.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/ExamplePlugin.dll",
    )
    mod.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/ExamplePlugin.dll"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["installed_files"] == [
        "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/ExamplePlugin.dll"
    ]


def test_scpsl_mod_apply_installs_archive_with_dependencies(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")
    archive_root = tmp_path / "archive"
    plugin_dir = archive_root / "plugins" / "global"
    dependency_dir = archive_root / "dependencies" / "global"
    plugin_dir.mkdir(parents=True)
    dependency_dir.mkdir(parents=True)
    (plugin_dir / "ArchivePlugin.dll").write_text("plugin", encoding="utf-8")
    (dependency_dir / "SharedDependency.dll").write_text("dependency", encoding="utf-8")

    archive_path = tmp_path / "scpsl-plugin-pack.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "ArchivePlugin.dll", "plugins/global/ArchivePlugin.dll")
        zf.write(
            dependency_dir / "SharedDependency.dll",
            "dependencies/global/SharedDependency.dll",
        )

    monkeypatch.setattr(
        MAIN_MODULE,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    mod.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/scpsl-plugin-pack.zip",
    )
    mod.command_functions["mod"](server, "apply")

    plugin_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/ArchivePlugin.dll"
    )
    dependency_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/dependencies/global/SharedDependency.dll"
    )
    assert plugin_file.exists()
    assert dependency_file.exists()


def test_scpsl_mod_apply_installs_curated_plugin_dll(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")
    plugin_dll = tmp_path / "BetterHelpCommand_LabAPI.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        MAIN_MODULE,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    mod.command_functions["mod"](server, "add", "manifest", "betterhelpcommand")
    mod.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/BetterHelpCommand_LabAPI.dll"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "curated"


def test_scpsl_mod_apply_installs_escapeplan_curated_plugin_dll(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")
    plugin_dll = tmp_path / "EscapePlan.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        MAIN_MODULE,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    mod.command_functions["mod"](server, "add", "manifest", "escapeplan")
    mod.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/EscapePlan.dll"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "escapeplan.3.0"


def test_scpsl_mod_apply_installs_respawntimer_curated_plugin_dll(
    tmp_path, monkeypatch
):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")
    plugin_dll = tmp_path / "RespawnTimer.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        MAIN_MODULE,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    mod.command_functions["mod"](server, "add", "manifest", "respawntimer")
    mod.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/RespawnTimer.dll"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "respawntimer.1.3.0"


def test_scpsl_mod_cleanup_removes_only_tracked_plugin_files(tmp_path):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root")

    tracked_plugin = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/TrackedPlugin.dll"
    )
    untracked_plugin = (
        Path(server.data["dir"])
        / "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/ManualPlugin.dll"
    )
    cache_file = Path(server.data["dir"]) / ".alphagsm" / "mods" / "scpslserver" / "cache.tmp"
    tracked_plugin.parent.mkdir(parents=True, exist_ok=True)
    tracked_plugin.write_text("tracked", encoding="utf-8")
    untracked_plugin.write_text("manual", encoding="utf-8")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("cache", encoding="utf-8")

    server.data["mods"]["installed"] = [
        {
            "source_type": "url",
            "resolved_id": "url.deadbeef.TrackedPlugin.dll",
            "installed_files": [
                "home/.config/SCP Secret Laboratory/LabAPI/plugins/global/TrackedPlugin.dll"
            ],
        }
    ]

    mod.command_functions["mod"](server, "cleanup")

    assert not tracked_plugin.exists()
    assert untracked_plugin.exists()
    assert not cache_file.exists()
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "moddb": []}