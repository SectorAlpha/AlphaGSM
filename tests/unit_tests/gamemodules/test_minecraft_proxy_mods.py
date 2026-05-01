from pathlib import Path
import json
import shutil

import pytest

import gamemodules.minecraft.bungeecord as bungeecord
import gamemodules.minecraft.velocity as velocity
import gamemodules.minecraft.waterfall as waterfall


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="proxymods"):
        self.name = name
        self.data = DummyData()


def _configure_proxy(module, server, target_dir, monkeypatch):
    if module is bungeecord:
        module.configure(server, ask=False, dir=str(target_dir))
        return

    jar_name = "velocity.jar" if module is velocity else "waterfall.jar"
    version = "3.4.0" if module is velocity else "1.21.10"
    monkeypatch.setattr(
        module,
        "resolve_download",
        lambda project, version=None: (version or "ignored", f"https://example.com/{jar_name}"),
    )
    module.configure(server, ask=False, dir=str(target_dir), version=version)


def _write_proxy_registry(tmp_path):
    registry_path = tmp_path / "curated_proxy_plugins.json"
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
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return registry_path


@pytest.mark.parametrize(
    "module,server_name,expected_registry",
    [
        (bungeecord, "bungee", "curated_proxy_plugins.json"),
        (velocity, "velocity", "curated_velocity_plugins.json"),
        (waterfall, "waterfall", "curated_proxy_plugins.json"),
    ],
)
def test_proxy_manifest_loader_selects_variant_registry(
    module, server_name, expected_registry, tmp_path, monkeypatch
):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    seen_paths = []
    sentinel = object()

    def _fake_load(path):
        seen_paths.append(Path(path).name)
        return sentinel

    monkeypatch.setattr(bungeecord.CuratedRegistryLoader, "load", staticmethod(_fake_load))

    assert bungeecord.load_proxy_curated_registry(server) is sentinel
    assert seen_paths == [expected_registry]


@pytest.mark.parametrize(
    "module,server_name,cache_dirname",
    [
        (bungeecord, "bungee", "minecraft-bungeecord"),
        (velocity, "velocity", "minecraft-velocity"),
        (waterfall, "waterfall", "minecraft-waterfall"),
    ],
)
def test_proxy_mod_add_url_persists_entry(module, server_name, cache_dirname, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)

    module.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/TestPlugin.jar",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["filename"] == "TestPlugin.jar"
    assert server.data["mod_cache_dirname"] == cache_dirname


@pytest.mark.parametrize(
    "module,server_name,cache_dirname",
    [
        (bungeecord, "bungee", "minecraft-bungeecord"),
        (velocity, "velocity", "minecraft-velocity"),
        (waterfall, "waterfall", "minecraft-waterfall"),
    ],
)
def test_proxy_mod_add_moddb_persists_entry(module, server_name, cache_dirname, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    monkeypatch.setattr(
        bungeecord,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "ProxyPlugins.zip",
        },
    )

    module.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack",
    )

    entry = server.data["mods"]["desired"]["moddb"][0]
    assert entry["resolved_id"] == "moddb.downloads.308604"
    assert server.data["mod_cache_dirname"] == cache_dirname


@pytest.mark.parametrize(
    "module,server_name,cache_dirname",
    [
        (bungeecord, "bungee", "minecraft-bungeecord"),
        (velocity, "velocity", "minecraft-velocity"),
        (waterfall, "waterfall", "minecraft-waterfall"),
    ],
)
def test_proxy_mod_add_manifest_persists_entry(module, server_name, cache_dirname, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    monkeypatch.setenv("ALPHAGSM_PROXY_CURATED_MODS_PATH", str(_write_proxy_registry(tmp_path)))

    module.command_functions["mod"](server, "add", "manifest", "viaversion")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["resolved_id"] == "viaversion.stable"
    assert server.data["mod_cache_dirname"] == cache_dirname


@pytest.mark.parametrize(
    "module,server_name",
    [
        (bungeecord, "bungee"),
        (velocity, "velocity"),
        (waterfall, "waterfall"),
    ],
)
def test_proxy_mod_apply_installs_plugin_jar(module, server_name, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    plugin_jar = tmp_path / f"{server_name}-plugin.jar"
    plugin_jar.write_text("jar-data", encoding="utf-8")
    monkeypatch.setattr(
        bungeecord,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_jar, target_path
        ),
    )

    module.command_functions["mod"](
        server,
        "add",
        "url",
        "https://plugins.example.invalid/TestPlugin.jar",
    )
    module.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / "TestPlugin.jar"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "url"


@pytest.mark.parametrize(
    "module,server_name",
    [
        (bungeecord, "bungee"),
        (velocity, "velocity"),
        (waterfall, "waterfall"),
    ],
)
def test_proxy_mod_apply_installs_moddb_archive(module, server_name, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    archive_root = tmp_path / f"{server_name}-archive"
    plugin_dir = archive_root / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "ArchivePlugin.jar").write_text("jar-data", encoding="utf-8")
    archive_path = tmp_path / f"{server_name}-plugins.zip"

    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "ArchivePlugin.jar", "plugins/ArchivePlugin.jar")

    monkeypatch.setattr(
        bungeecord,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "ProxyPlugins.zip",
        },
    )
    monkeypatch.setattr(
        bungeecord,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    module.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack",
    )
    module.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / "ArchivePlugin.jar"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "moddb"


@pytest.mark.parametrize(
    "module,server_name",
    [
        (bungeecord, "bungee"),
        (velocity, "velocity"),
        (waterfall, "waterfall"),
    ],
)
def test_proxy_mod_apply_installs_manifest_plugin(module, server_name, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    monkeypatch.setenv("ALPHAGSM_PROXY_CURATED_MODS_PATH", str(_write_proxy_registry(tmp_path)))
    plugin_jar = tmp_path / f"{server_name}-manifest-plugin.jar"
    plugin_jar.write_text("jar-data", encoding="utf-8")
    monkeypatch.setattr(
        bungeecord,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            plugin_jar, target_path
        ),
    )

    module.command_functions["mod"](server, "add", "manifest", "viaversion")
    module.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / "ViaVersion-5.9.0.jar"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "curated"


@pytest.mark.parametrize(
    "module,server_name",
    [
        (bungeecord, "bungee"),
        (velocity, "velocity"),
        (waterfall, "waterfall"),
    ],
)
def test_proxy_mod_apply_installs_manifest_stack(module, server_name, tmp_path, monkeypatch):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    monkeypatch.setenv("ALPHAGSM_PROXY_CURATED_MODS_PATH", str(_write_proxy_registry(tmp_path)))
    jar_sources = {
        "ViaVersion-5.9.0.jar": tmp_path / "ViaVersion-5.9.0.jar",
        "ViaBackwards-5.9.0.jar": tmp_path / "ViaBackwards-5.9.0.jar",
        "ViaRewind-4.1.0.jar": tmp_path / "ViaRewind-4.1.0.jar",
    }
    for path in jar_sources.values():
        path.write_text("jar-data", encoding="utf-8")

    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        shutil.copy2(jar_sources[target_path.name], target_path)

    monkeypatch.setattr(bungeecord, "download_to_cache", _fake_download)

    module.command_functions["mod"](server, "add", "manifest", "viarewind")
    module.command_functions["mod"](server, "apply")

    assert (Path(server.data["dir"]) / "plugins" / "ViaVersion-5.9.0.jar").exists()
    assert (Path(server.data["dir"]) / "plugins" / "ViaBackwards-5.9.0.jar").exists()
    assert (Path(server.data["dir"]) / "plugins" / "ViaRewind-4.1.0.jar").exists()
    assert {entry["resolved_id"] for entry in server.data["mods"]["installed"]} == {
        "viaversion.stable",
        "viabackwards.stable",
        "viarewind.stable",
    }


@pytest.mark.parametrize(
    "module,server_name,expected_filename",
    [
        (bungeecord, "bungee", "LuckPerms-Bungee-5.5.17.jar"),
        (velocity, "velocity", "LuckPerms-Velocity-5.5.17.jar"),
        (waterfall, "waterfall", "LuckPerms-Bungee-5.5.17.jar"),
    ],
)
def test_proxy_mod_apply_installs_variant_specific_manifest_plugin(
    module, server_name, expected_filename, tmp_path, monkeypatch
):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)
    jar_sources = {
        "LuckPerms-Bungee-5.5.17.jar": tmp_path / "LuckPerms-Bungee-5.5.17.jar",
        "LuckPerms-Velocity-5.5.17.jar": tmp_path / "LuckPerms-Velocity-5.5.17.jar",
    }
    for path in jar_sources.values():
        path.write_text("jar-data", encoding="utf-8")

    def _fake_download(url, *, allowed_hosts, target_path, checksum=None):
        shutil.copy2(jar_sources[target_path.name], target_path)

    monkeypatch.setattr(bungeecord, "download_to_cache", _fake_download)

    module.command_functions["mod"](server, "add", "manifest", "luckperms")
    module.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "plugins" / expected_filename
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "luckperms.stable"


@pytest.mark.parametrize(
    "module,server_name,cache_dirname",
    [
        (bungeecord, "bungee", "minecraft-bungeecord"),
        (velocity, "velocity", "minecraft-velocity"),
        (waterfall, "waterfall", "minecraft-waterfall"),
    ],
)
def test_proxy_mod_cleanup_removes_only_tracked_plugin_files(
    module, server_name, cache_dirname, tmp_path, monkeypatch
):
    server = DummyServer(server_name)
    _configure_proxy(module, server, tmp_path / server_name, monkeypatch)

    tracked_plugin = Path(server.data["dir"]) / "plugins" / "TrackedPlugin.jar"
    untracked_plugin = Path(server.data["dir"]) / "plugins" / "ManualPlugin.jar"
    cache_file = Path(server.data["dir"]) / ".alphagsm" / "mods" / cache_dirname / "cache.tmp"
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

    module.command_functions["mod"](server, "cleanup")

    assert not tracked_plugin.exists()
    assert untracked_plugin.exists()
    assert not cache_file.exists()
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "moddb": []}