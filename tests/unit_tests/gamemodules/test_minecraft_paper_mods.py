from pathlib import Path
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
    assert server.data["mods"]["desired"]["url"] == []


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
    assert server.data["mods"]["desired"] == {"url": []}