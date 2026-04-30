"""Tests for TF2 mod desired-state defaults and command handlers."""

import http.server
import json
from pathlib import Path
import shutil
import socket
import socketserver
import tarfile
import threading
import zipfile

import pytest

import gamemodules.teamfortress2 as tf2
import gamemodules.teamfortress2.mods as tf2_mods
from server import ServerError


class DummyData(dict):
    """Minimal datastore double used by TF2 module tests."""

    def save(self):
        self.saved = True


class DummyServer:
    """Minimal server double used by TF2 module tests."""

    def __init__(self):
        self.name = "tf2mods"
        self.data = DummyData()


def test_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer()

    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["gamebanana"] == []
    assert server.data["mods"]["desired"]["workshop"] == []


def test_mod_add_curated_uses_default_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "sourcemod"
    assert entry["resolved_id"] == "sourcemod.stable"


def test_mod_add_manifest_alias_uses_curated_registry(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "manifest", "sourcemod")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "sourcemod"
    assert entry["resolved_id"] == "sourcemod.stable"


def test_mod_add_curated_rejects_duplicate_requested_entry(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "curated", "sourcemod")


def test_mod_add_curated_accepts_explicit_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod", "1.12")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["resolved_id"] == "sourcemod.1.12"


def test_mod_add_curated_requires_identifier(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="requires a curated family identifier"):
        tf2.command_functions["mod"](server, "add", "curated")


def test_mod_add_curated_rejects_unknown_family_with_server_error(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown curated mod family: not-a-family"):
        tf2.command_functions["mod"](server, "add", "curated", "not-a-family")


def test_mod_add_curated_rejects_unknown_channel_with_server_error(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown curated mod release: sourcemod.bad-channel"):
        tf2.command_functions["mod"](server, "add", "curated", "sourcemod", "bad-channel")


def test_mod_add_workshop_accepts_numeric_id_only(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")
    assert server.data["mods"]["desired"]["workshop"][0]["workshop_id"] == "1234567890"
    assert server.data["mods"]["desired"]["workshop"][0]["resolved_id"] == "workshop.1234567890"

    with pytest.raises(ServerError, match="numeric workshop id"):
        tf2.command_functions["mod"](server, "add", "workshop", "map_bad")


def test_mod_add_workshop_rejects_duplicate_id(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "workshop", "1234567890")


def test_mod_add_gamebanana_resolves_and_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))
    monkeypatch.setattr(
        tf2_mods,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "file_id": "777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "tf2mod.zip",
        },
    )

    tf2.command_functions["mod"](server, "add", "gamebanana", "12345")

    entry = server.data["mods"]["desired"]["gamebanana"][0]
    assert entry["requested_id"] == "12345"
    assert entry["resolved_id"] == "gamebanana.12345.777"


def test_mod_add_gamebanana_rejects_duplicate_requested_entry(tmp_path, monkeypatch):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))
    monkeypatch.setattr(
        tf2_mods,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "file_id": "777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "tf2mod.zip",
        },
    )

    tf2.command_functions["mod"](server, "add", "gamebanana", "12345")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "gamebanana", "12345")


def test_mod_apply_installs_curated_entry_from_override_registry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    archive_root = tmp_path / "archive-root"
    payload = archive_root / "addons" / "sourcemod" / "plugins"
    payload.mkdir(parents=True)
    (payload / "base.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "sourcemod.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(archive_root / "addons", arcname="addons")
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "sourcemod": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/sourcemod.tar.gz",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "tar.gz",
                                "destinations": ["addons"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    monkeypatch.setenv("ALPHAGSM_TF2_CURATED_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr(
        tf2_mods,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")
    tf2.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "base.smx"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "sourcemod.stable"


def test_mod_apply_installs_workshop_entry_from_downloaded_item(tmp_path, monkeypatch):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))
    workshop_root = tmp_path / "workshop-cache" / "steamapps" / "workshop" / "content" / "440" / "1234567890"
    payload = workshop_root / "addons" / "sourcemod" / "plugins"
    payload.mkdir(parents=True)
    (payload / "from_workshop.smx").write_text("plugin", encoding="utf-8")
    monkeypatch.setattr(
        tf2_mods.steamcmd,
        "download_workshop_item",
        lambda path, workshop_app_id, workshop_item_id, steam_anonymous_login_possible: str(
            workshop_root
        ),
    )

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")
    tf2.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "from_workshop.smx"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "workshop.1234567890"


def test_mod_apply_clears_previous_errors_after_success(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    archive_root = tmp_path / "archive-root"
    payload = archive_root / "addons" / "sourcemod" / "plugins"
    payload.mkdir(parents=True)
    (payload / "base.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "sourcemod.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(archive_root / "addons", arcname="addons")
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "sourcemod": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/sourcemod.tar.gz",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "tar.gz",
                                "destinations": ["addons"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    server.data["mods"]["errors"] = ["old error"]
    monkeypatch.setenv("ALPHAGSM_TF2_CURATED_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr(
        tf2_mods,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")
    tf2.command_functions["mod"](server, "apply")

    assert server.data["mods"]["errors"] == []
    assert server.data["mods"]["last_apply"] == "success"


def test_mod_apply_installs_gamebanana_zip_entry(tmp_path, monkeypatch):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "tf" / "addons" / "sourcemod" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "banana.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "banana.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "banana.smx", "tf/addons/sourcemod/plugins/banana.smx")

    monkeypatch.setattr(
        tf2_mods,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "file_id": "777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "banana.zip",
        },
    )
    monkeypatch.setattr(
        tf2_mods,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tf2.command_functions["mod"](server, "add", "gamebanana", "12345")
    tf2.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "banana.smx"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "gamebanana.12345.777"


def test_mod_cleanup_removes_installed_files_and_resets_state(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    installed_file = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "cleanup.smx"
    )
    installed_file.parent.mkdir(parents=True)
    installed_file.write_text("plugin", encoding="utf-8")
    cache_file = Path(server.data["dir"]) / ".alphagsm" / "mods" / "cached.txt"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("cache", encoding="utf-8")
    server.data["mods"]["desired"]["curated"].append(
        {"requested_id": "sourcemod", "resolved_id": "sourcemod.stable", "channel": "stable"}
    )
    server.data["mods"]["desired"]["gamebanana"].append(
        {
            "requested_id": "12345",
            "resolved_id": "gamebanana.12345.777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "banana.zip",
        }
    )
    server.data["mods"]["desired"]["workshop"].append(
        {"workshop_id": "1234567890", "resolved_id": "workshop.1234567890"}
    )
    server.data["mods"]["installed"] = [
        {
            "source_type": "gamebanana",
            "resolved_id": "gamebanana.12345.777",
            "installed_files": ["tf/addons/sourcemod/plugins/cleanup.smx"],
        }
    ]
    server.data["mods"]["errors"] = ["old error"]

    tf2.command_functions["mod"](server, "cleanup")

    assert not installed_file.exists()
    assert not cache_file.exists()
    assert server.data["mods"]["desired"] == {
        "curated": [],
        "gamebanana": [],
        "workshop": [],
    }
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["errors"] == []
    assert server.data["mods"]["last_apply"] == "cleanup"


def test_mod_cleanup_removes_only_files_recorded_per_mod(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))

    first_owned = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "first.smx"
    )
    second_owned = (
        Path(server.data["dir"]) / "tf" / "addons" / "metamod" / "bin" / "second.vdf"
    )
    unowned_file = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "manual.smx"
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
            "installed_files": ["tf/addons/sourcemod/plugins/first.smx"],
        },
        {
            "source_type": "workshop",
            "resolved_id": "workshop.1234567890",
            "installed_files": ["tf/addons/metamod/bin/second.vdf"],
        },
    ]

    tf2.command_functions["mod"](server, "cleanup")

    assert not first_owned.exists()
    assert not second_owned.exists()
    assert unowned_file.exists()


def _make_sourcemod_archive(tmp_path):
    """Build a minimal fake sourcemod tar.gz for local HTTP tests."""
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "addons" / "sourcemod" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "base.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "sourcemod.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(archive_root / "addons", arcname="addons")
    return archive_path


def _start_local_http_server(serve_dir: Path):
    """Start a temporary HTTP server on 127.0.0.1 and return (httpd, port, thread)."""
    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def log_message(self, fmt, *args):  # pylint: disable=arguments-differ
            return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    httpd = socketserver.TCPServer(("127.0.0.1", port), _QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port, thread


def test_mod_apply_downloads_via_real_http_and_installs(tmp_path, monkeypatch):
    """apply exercises download_to_cache over a real local HTTP server.

    Unlike tests that monkeypatch download_to_cache away entirely, this test
    lets the actual HTTP download path run so that the host-allowlist check,
    streaming write, and SHA-less cache placement are all covered.
    """
    archive_path = _make_sourcemod_archive(tmp_path)

    httpd, port, _thread = _start_local_http_server(tmp_path)
    try:
        registry_path = tmp_path / "curated_mods.json"
        registry_path.write_text(
            json.dumps(
                {
                    "families": {
                        "sourcemod": {
                            "default": "stable",
                            "releases": {
                                "stable": {
                                    "url": f"http://127.0.0.1:{port}/{archive_path.name}",
                                    "hosts": ["127.0.0.1"],
                                    "archive_type": "tar.gz",
                                    "destinations": ["addons"],
                                }
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("ALPHAGSM_TF2_CURATED_REGISTRY_PATH", str(registry_path))

        server = DummyServer()
        tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
        tf2.command_functions["mod"](server, "add", "curated", "sourcemod")
        tf2.command_functions["mod"](server, "apply")
    finally:
        httpd.shutdown()

    mods = server.data["mods"]
    assert mods["last_apply"] == "success"
    assert mods["errors"] == []
    assert any("sourcemod" in e["resolved_id"] for e in mods["installed"])
    installed_file = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "base.smx"
    )
    assert installed_file.exists()


def test_mod_add_curated_prophunt_resolves_from_builtin_registry(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "prophunt")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "prophunt"
    assert entry["resolved_id"] == "prophunt.stable"


def test_mod_apply_installs_curated_zip_entry(tmp_path, monkeypatch):
    """apply can install a zip-format mod archive (PropHunt path)."""
    import zipfile

    registry_path = tmp_path / "curated_mods.json"
    archive_root = tmp_path / "archive-root"
    plugin_dir = archive_root / "addons" / "sourcemod" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "prophunt.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "prophunt.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(plugin_dir / "prophunt.smx", "addons/sourcemod/plugins/prophunt.smx")

    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "prophunt": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/prophunt.zip",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "zip",
                                "destinations": ["addons"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    monkeypatch.setenv("ALPHAGSM_TF2_CURATED_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr(
        tf2_mods,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    tf2.command_functions["mod"](server, "add", "curated", "prophunt")
    tf2.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"]) / "tf" / "addons" / "sourcemod" / "plugins" / "prophunt.smx"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "prophunt.stable"
