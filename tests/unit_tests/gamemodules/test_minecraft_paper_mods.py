from pathlib import Path
import json
import shutil
import zipfile

import pytest

import gamemodules.minecraft.paper as paper


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="papermods"):
        self.name = name
        self.data = DummyData()


def test_paper_configure_seeds_mod_state_defaults(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )

    paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["url"] == []
    assert server.data["mods"]["desired"]["moddb"] == []


def _write_paper_registry(tmp_path):
    registry_path = tmp_path / "curated_paper_plugins.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "viaversion": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/ViaVersion/ViaVersion/releases/download/5.9.0/ViaVersion-5.9.0.jar",
                                "hosts": ["github.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                            }
                        },
                    },
                    "viabackwards": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/ViaVersion/ViaBackwards/releases/download/5.9.0/ViaBackwards-5.9.0.jar",
                                "hosts": ["github.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                                "dependencies": ["viaversion"],
                            }
                        },
                    },
                    "viarewind": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/ViaVersion/ViaRewind/releases/download/4.1.0/ViaRewind-4.1.0.jar",
                                "hosts": ["github.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                                "dependencies": ["viabackwards"],
                            }
                        },
                    },
                    "luckperms": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://cdn.modrinth.com/data/Vebnzrzj/versions/OrIs0S6b/LuckPerms-Bukkit-5.5.17.jar",
                                "hosts": ["cdn.modrinth.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                            }
                        },
                    },
                    "essentialsx": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/EssentialsX/Essentials/releases/download/2.21.2/EssentialsX-2.21.2.jar",
                                "hosts": ["github.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                            }
                        },
                    },
                    "essentialsxchat": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/EssentialsX/Essentials/releases/download/2.21.2/EssentialsXChat-2.21.2.jar",
                                "hosts": ["github.com"],
                                "archive_type": "jar",
                                "destinations": ["plugins"],
                                "dependencies": ["essentialsx"],
                            }
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def test_paper_mod_add_manifest_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    monkeypatch.setenv("ALPHAGSM_PAPER_CURATED_MODS_PATH", str(_write_paper_registry(tmp_path)))
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    paper.command_functions["mod"](server, "add", "manifest", "viaversion")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "viaversion"
    assert entry["resolved_id"] == "viaversion.stable"


def test_paper_mod_add_url_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    paper.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/TestPlugin.jar",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["requested_id"] == "https://plugins.example.invalid/TestPlugin.jar"
    assert entry["filename"] == "TestPlugin.jar"


def test_paper_mod_add_url_rejects_non_jar_filename(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    with pytest.raises(paper.ServerError, match="plugin .jar filename"):
        paper.command_functions["mod"](
            server,
            "add",
            "url",
            "https://plugins.example.invalid/download",
        )


def test_paper_mod_add_moddb_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    monkeypatch.setattr(
        paper,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "PaperPlugins.zip",
        },
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    paper.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/paper-plugin-pack/downloads/paper-plugin-pack",
    )

    entry = server.data["mods"]["desired"]["moddb"][0]
    assert entry["requested_id"] == "https://www.moddb.com/mods/paper-plugin-pack/downloads/paper-plugin-pack"
    assert entry["resolved_id"] == "moddb.downloads.308604"


def test_paper_mod_apply_installs_plugin_jar(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))
    plugin_jar = tmp_path / "TestPlugin.jar"
    plugin_jar.write_text("jar-data", encoding="utf-8")
    monkeypatch.setattr(
        paper,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_jar, target_path
        ),
    )

    paper.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/TestPlugin.jar",
    )
    paper.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / "TestPlugin.jar"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "url"


def test_paper_mod_cleanup_removes_only_tracked_plugin_files(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))

    tracked_plugin = Path(server.data["dir"]) / "plugins" / "TrackedPlugin.jar"
    untracked_plugin = Path(server.data["dir"]) / "plugins" / "ManualPlugin.jar"
    cache_file = Path(server.data["dir"]) / ".alphagsm" / "mods" / "minecraft-paper" / "cache.tmp"
    tracked_plugin.parent.mkdir(parents=True)
    tracked_plugin.write_text("tracked", encoding="utf-8")
    untracked_plugin.write_text("manual", encoding="utf-8")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("cache", encoding="utf-8")

    server.data["mods"]["installed"] = [
        {
            "source_type": "url",
            "resolved_id": "url.deadbeef.TrackedPlugin.jar",
            "installed_files": ["plugins/TrackedPlugin.jar"],
        }
    ]

    paper.command_functions["mod"](server, "cleanup")

    assert not tracked_plugin.exists()
    assert untracked_plugin.exists()
    assert not cache_file.exists()
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "moddb": []}


def test_paper_mod_apply_installs_moddb_archive(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "ArchivePlugin.jar").write_text("jar-data", encoding="utf-8")
    archive_path = tmp_path / "paper-plugins.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "ArchivePlugin.jar", "plugins/ArchivePlugin.jar")

    monkeypatch.setattr(
        paper,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "PaperPlugins.zip",
        },
    )
    monkeypatch.setattr(
        paper,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    paper.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/paper-plugin-pack/downloads/paper-plugin-pack",
    )
    paper.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / "ArchivePlugin.jar"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "moddb"


def test_paper_mod_apply_installs_manifest_stack(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    monkeypatch.setenv("ALPHAGSM_PAPER_CURATED_MODS_PATH", str(_write_paper_registry(tmp_path)))
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))

    jar_sources = {
        "ViaVersion-5.9.0.jar": tmp_path / "ViaVersion-5.9.0.jar",
        "ViaBackwards-5.9.0.jar": tmp_path / "ViaBackwards-5.9.0.jar",
        "ViaRewind-4.1.0.jar": tmp_path / "ViaRewind-4.1.0.jar",
    }
    for path in jar_sources.values():
        path.write_text("jar-data", encoding="utf-8")

    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        shutil.copy2(jar_sources[target_path.name], target_path)

    monkeypatch.setattr(paper, "download_to_cache", _fake_download)

    paper.command_functions["mod"](server, "add", "manifest", "viarewind")
    paper.command_functions["mod"](server, "apply")

    assert (Path(server.data["dir"]) / "plugins" / "ViaVersion-5.9.0.jar").exists()
    assert (Path(server.data["dir"]) / "plugins" / "ViaBackwards-5.9.0.jar").exists()
    assert (Path(server.data["dir"]) / "plugins" / "ViaRewind-4.1.0.jar").exists()
    assert {entry["resolved_id"] for entry in server.data["mods"]["installed"]} == {
        "viaversion.stable",
        "viabackwards.stable",
        "viarewind.stable",
    }


def test_paper_mod_apply_installs_modrinth_manifest_plugin(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    monkeypatch.setenv("ALPHAGSM_PAPER_CURATED_MODS_PATH", str(_write_paper_registry(tmp_path)))
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))

    plugin_jar = tmp_path / "LuckPerms-Bukkit-5.5.17.jar"
    plugin_jar.write_text("jar-data", encoding="utf-8")

    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        assert allowed_hosts == ["cdn.modrinth.com"]
        shutil.copy2(plugin_jar, target_path)

    monkeypatch.setattr(paper, "download_to_cache", _fake_download)

    paper.command_functions["mod"](server, "add", "manifest", "luckperms")
    paper.command_functions["mod"](server, "apply")

    assert (Path(server.data["dir"]) / "plugins" / "LuckPerms-Bukkit-5.5.17.jar").exists()
    assert {entry["resolved_id"] for entry in server.data["mods"]["installed"]} == {
        "luckperms.stable",
    }


def test_paper_mod_apply_installs_essentialsx_dependency_pair(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "https://example.com/paper.jar"),
    )
    monkeypatch.setenv("ALPHAGSM_PAPER_CURATED_MODS_PATH", str(_write_paper_registry(tmp_path)))
    paper.configure(server, ask=False, port=25565, dir=str(tmp_path / "server-root"))

    jar_sources = {
        "EssentialsX-2.21.2.jar": tmp_path / "EssentialsX-2.21.2.jar",
        "EssentialsXChat-2.21.2.jar": tmp_path / "EssentialsXChat-2.21.2.jar",
    }
    for path in jar_sources.values():
        path.write_text("jar-data", encoding="utf-8")

    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        shutil.copy2(jar_sources[target_path.name], target_path)

    monkeypatch.setattr(paper, "download_to_cache", _fake_download)

    paper.command_functions["mod"](server, "add", "manifest", "essentialsxchat")
    paper.command_functions["mod"](server, "apply")

    assert (Path(server.data["dir"]) / "plugins" / "EssentialsX-2.21.2.jar").exists()
    assert (Path(server.data["dir"]) / "plugins" / "EssentialsXChat-2.21.2.jar").exists()
    assert {entry["resolved_id"] for entry in server.data["mods"]["installed"]} == {
        "essentialsx.stable",
        "essentialsxchat.stable",
    }