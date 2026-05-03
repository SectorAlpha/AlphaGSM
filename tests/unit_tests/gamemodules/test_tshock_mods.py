from pathlib import Path
import json
import shutil
import tarfile

import pytest

import gamemodules.terraria.tshock as tshock


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="tshockmods"):
        self.name = name
        self.data = DummyData()


def _configure_server(server, tmp_path, monkeypatch):
    monkeypatch.setattr(
        tshock,
        "resolve_tshock_download",
        lambda: ("v5.2.3", "https://example.com/tshock.zip"),
    )
    tshock.configure(server, ask=False, port=7778, dir=str(tmp_path))


def test_tshock_configure_seeds_mod_state_defaults(tmp_path, monkeypatch):
    server = DummyServer()

    _configure_server(server, tmp_path, monkeypatch)

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["url"] == []
    assert server.data["mods"]["desired"]["moddb"] == []


def test_tshock_mod_add_manifest_persists_entry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_plugins.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "banguard": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/BanGuard.dll",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "dll",
                                "destinations": ["ServerPlugins"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_TSHOCK_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    tshock.command_functions["mod"](server, "add", "manifest", "banguard")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "banguard"
    assert entry["resolved_id"] == "banguard.stable"


@pytest.mark.parametrize(
    "family,expected_resolved_id,archive_type,filename",
    [
        ("perplayerloot", "perplayerloot.stable", "dll", "PerPlayerLoot.dll"),
        ("autoteam", "autoteam.stable", "dll", "AutoTeam.dll"),
        ("facommands", "facommands.stable", "dll", "FACommands.dll"),
        ("omni", "omni.stable", "zip", "Artifact.zip"),
        ("timeranks", "timeranks.1.1", "dll", "TimeRanks.dll"),
        ("ranksystem", "ranksystem.2.0.5", "dll", "RankSystem.dll"),
        ("qol", "qol.v1.3.3", "dll", "QoL.dll"),
        ("replenisher", "replenisher.v1.2.4", "dll", "Replenisher.dll"),
        ("bagger", "bagger.v1.3.1", "dll", "Bagger.dll"),
        ("tslootchest", "tslootchest.v1.4.0", "zip", "TSLootChest-v1.4.0.zip"),
    ],
)
def test_tshock_checked_in_manifest_resolves_verified_plugin_family(
    family, expected_resolved_id, archive_type, filename, monkeypatch
):
    monkeypatch.delenv("ALPHAGSM_TSHOCK_CURATED_MODS_PATH", raising=False)

    resolved = tshock.load_tshock_curated_registry().resolve(family)

    assert resolved.resolved_id == expected_resolved_id
    assert resolved.archive_type == archive_type
    assert list(resolved.hosts) == ["github.com"]
    assert resolved.url.endswith(f"/{filename}")
    assert list(resolved.destinations) == ["ServerPlugins"]


def test_tshock_mod_add_url_persists_dll_entry(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    tshock.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/ExamplePlugin.dll",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["requested_id"] == "https://plugins.example.invalid/ExamplePlugin.dll"
    assert entry["filename"] == "ExamplePlugin.dll"
    assert entry["archive_type"] == "dll"


def test_tshock_mod_add_url_rejects_invalid_filename(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    with pytest.raises(tshock.ServerError, match="plugin .dll or .zip filename"):
        tshock.command_functions["mod"](
            server,
            "add",
            "url",
            "https://plugins.example.invalid/download",
        )


def test_tshock_mod_add_moddb_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)
    monkeypatch.setattr(
        tshock,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "TShockPlugins.zip",
        },
    )

    tshock.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/tshock-plugin-pack/downloads/tshock-plugin-pack",
    )

    entry = server.data["mods"]["desired"]["moddb"][0]
    assert entry["requested_id"] == "https://www.moddb.com/mods/tshock-plugin-pack/downloads/tshock-plugin-pack"
    assert entry["resolved_id"] == "moddb.downloads.308604"


def test_tshock_mod_apply_installs_plugin_dll(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    plugin_dll = tmp_path / "ExamplePlugin.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        tshock,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    tshock.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/ExamplePlugin.dll",
    )
    tshock.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "ServerPlugins" / "ExamplePlugin.dll"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "url"


def test_tshock_mod_cleanup_removes_only_tracked_plugin_files(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)

    tracked_plugin = Path(server.data["dir"]) / "ServerPlugins" / "TrackedPlugin.dll"
    untracked_plugin = Path(server.data["dir"]) / "ServerPlugins" / "ManualPlugin.dll"
    cache_file = Path(server.data["dir"]) / ".alphagsm" / "mods" / "terraria-tshock" / "cache.tmp"
    tracked_plugin.parent.mkdir(parents=True)
    tracked_plugin.write_text("tracked", encoding="utf-8")
    untracked_plugin.write_text("manual", encoding="utf-8")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("cache", encoding="utf-8")

    server.data["mods"]["installed"] = [
        {
            "source_type": "url",
            "resolved_id": "url.deadbeef.TrackedPlugin.dll",
            "installed_files": ["ServerPlugins/TrackedPlugin.dll"],
        }
    ]

    tshock.command_functions["mod"](server, "cleanup")

    assert not tracked_plugin.exists()
    assert untracked_plugin.exists()
    assert not cache_file.exists()
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "moddb": []}


def test_tshock_mod_apply_installs_curated_plugin_dll(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_plugins.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "smartregions": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/SmartRegions.dll",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "dll",
                                "destinations": ["ServerPlugins"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_TSHOCK_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    plugin_dll = tmp_path / "SmartRegions.dll"
    plugin_dll.write_text("dll-data", encoding="utf-8")
    monkeypatch.setattr(
        tshock,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_dll, target_path
        ),
    )

    tshock.command_functions["mod"](server, "add", "curated", "smartregions")
    tshock.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "ServerPlugins" / "SmartRegions.dll"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "smartregions.stable"


def test_tshock_mod_apply_installs_curated_archive_with_bare_plugin_root(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_plugins.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "omni": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/Artifact.zip",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "zip",
                                "destinations": ["ServerPlugins"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_TSHOCK_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)

    archive_path = tmp_path / "Artifact.zip"
    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("Artifact/ExamplePlugin.dll", "dll-data")
        zf.writestr("Artifact/ExamplePlugin.xml", "xml-data")
        zf.writestr("Artifact/tshock/Omni/config.json", "{}")
        zf.writestr("Artifact/README.md", "ignored")

    monkeypatch.setattr(
        tshock,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tshock.command_functions["mod"](server, "add", "curated", "omni")
    tshock.command_functions["mod"](server, "apply")

    server_root = Path(server.data["dir"])
    assert (server_root / "ServerPlugins" / "ExamplePlugin.dll").exists()
    assert (server_root / "ServerPlugins" / "ExamplePlugin.xml").exists()
    assert (server_root / "tshock" / "Omni" / "config.json").exists()
    assert not (server_root / "README.md").exists()


def test_tshock_mod_apply_installs_moddb_archive(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "ServerPlugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "ArchivePlugin.dll").write_text("dll-data", encoding="utf-8")
    archive_path = tmp_path / "tshock-plugins.zip"

    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "ArchivePlugin.dll", "ServerPlugins/ArchivePlugin.dll")

    monkeypatch.setattr(
        tshock,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "TShockPlugins.zip",
        },
    )
    monkeypatch.setattr(
        tshock,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tshock.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/tshock-plugin-pack/downloads/tshock-plugin-pack",
    )
    tshock.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "ServerPlugins" / "ArchivePlugin.dll"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "moddb"