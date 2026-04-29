"""Tests for TF2 mod desired-state defaults and command handlers."""

import http.server
import json
from pathlib import Path
import shutil
import socket
import socketserver
import tarfile
import threading

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
    assert server.data["mods"]["desired"]["workshop"] == []


def test_mod_add_curated_uses_default_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")

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

    with pytest.raises(ServerError, match="numeric workshop id"):
        tf2.command_functions["mod"](server, "add", "workshop", "map_bad")


def test_mod_add_workshop_rejects_duplicate_id(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "workshop", "1234567890")


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


def test_mod_apply_rejects_workshop_items_until_provider_is_verified(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))
    server.data["mods"]["desired"]["workshop"].append(
        {"workshop_id": "1234567890", "source_type": "workshop"}
    )

    with pytest.raises(ServerError, match="Workshop support is experimental"):
        tf2.command_functions["mod"](server, "apply")

    assert server.data["mods"]["errors"] == [
        "Workshop support is experimental until a verified TF2 provider is implemented"
    ]


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
