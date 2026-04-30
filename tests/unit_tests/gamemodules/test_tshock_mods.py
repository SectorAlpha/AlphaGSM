from pathlib import Path
import shutil

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
    assert server.data["mods"]["desired"]["url"] == []


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
    assert server.data["mods"]["desired"] == {"url": []}