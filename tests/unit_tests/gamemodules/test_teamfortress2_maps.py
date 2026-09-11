"""Tests for TF2 map desired-state defaults and command handlers."""

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
import gamemodules.teamfortress2.maps as tf2_maps
from server import ServerError


class DummyData(dict):
    """Minimal datastore double used by TF2 map module tests."""

    def save(self):
        self.saved = True


class DummyServer:
    """Minimal server double used by TF2 map module tests."""

    def __init__(self):
        self.name = "tf2maps"
        self.data = DummyData()


# ---------------------------------------------------------------------------
# Defaults and desired-state management
# ---------------------------------------------------------------------------


def test_configure_seeds_map_state_defaults(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    maps = server.data["maps"]
    assert maps["enabled"] is True
    assert maps["autoapply"] is True
    assert maps["desired"] == {"curated": []}
    assert maps["installed"] == []
    assert maps["last_apply"] is None
    assert maps["errors"] == []


def test_map_add_curated_uses_default_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["map"](server, "add", "curated", "cp_granary_pro_rc8")

    desired = server.data["maps"]["desired"]["curated"]
    assert len(desired) == 1
    assert desired[0]["requested_id"] == "cp_granary_pro_rc8"
    assert desired[0]["resolved_id"] == "cp_granary_pro_rc8.current"


def test_map_add_curated_rejects_duplicate(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["map"](server, "add", "curated", "cp_granary_pro_rc8")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["map"](server, "add", "curated", "cp_granary_pro_rc8")


def test_map_add_curated_requires_identifier(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Usage: map add curated"):
        tf2.command_functions["map"](server, "add", "curated")


def test_map_add_curated_rejects_unknown_map(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown curated mod family"):
        tf2.command_functions["map"](server, "add", "curated", "not_a_real_map")


def test_map_command_raises_for_unknown_action(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown map action"):
        tf2.command_functions["map"](server, "bad_action")


# ---------------------------------------------------------------------------
# BSP install via real local HTTP server
# ---------------------------------------------------------------------------


def _make_bsp_archive(tmp_path, filename="cp_test_map.bsp"):
    """Write a tiny fake .bsp file to tmp_path and return the path."""
    bsp = tmp_path / filename
    bsp.write_bytes(b"VBSP" + b"\x00" * 16)
    return bsp


def _make_registry_json(tmp_path, port, map_name, bsp_filename):
    """Create a curated_maps.json pointing at http://127.0.0.1:<port>."""
    registry_path = tmp_path / "curated_maps.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    map_name: {
                        "default": "current",
                        "releases": {
                            "current": {
                                "url": f"http://127.0.0.1:{port}/{bsp_filename}",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "bsp",
                                "destinations": ["tf/maps"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def _start_local_http_server(serve_dir: Path):
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


def test_map_apply_downloads_bsp_via_real_http(tmp_path, monkeypatch):
    """apply_configured_maps fetches a .bsp over a real local HTTP server
    and places it under tf/maps/ in the server install root."""
    map_name = "cp_test_map"
    bsp_path = _make_bsp_archive(tmp_path, f"{map_name}.bsp")

    httpd, port, _thread = _start_local_http_server(tmp_path)
    try:
        registry_path = _make_registry_json(tmp_path, port, map_name, bsp_path.name)
        monkeypatch.setenv("ALPHAGSM_TF2_CURATED_MAPS_PATH", str(registry_path))

        server = DummyServer()
        tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
        tf2.command_functions["map"](server, "add", "curated", map_name)
        tf2.command_functions["map"](server, "apply")
    finally:
        httpd.shutdown()

    maps = server.data["maps"]
    assert maps["last_apply"] == "success"
    assert maps["errors"] == []
    assert any(map_name in e["resolved_id"] for e in maps["installed"])
    installed_bsp = Path(server.data["dir"]) / "tf" / "maps" / f"{map_name}.bsp"
    assert installed_bsp.exists()


def test_map_apply_installs_tar_gz_map_pack(tmp_path, monkeypatch):
    """apply_configured_maps extracts a tar.gz map pack into the server."""
    map_name = "cp_mappack_example"
    archive_root = tmp_path / "archive-root"
    maps_dir = archive_root / "tf" / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / f"{map_name}.bsp").write_bytes(b"VBSP" + b"\x00" * 16)
    archive_path = tmp_path / f"{map_name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(archive_root / "tf", arcname="tf")

    httpd, port, _thread = _start_local_http_server(tmp_path)
    try:
        registry_path = tmp_path / "curated_maps.json"
        registry_path.write_text(
            json.dumps(
                {
                    "families": {
                        map_name: {
                            "default": "current",
                            "releases": {
                                "current": {
                                    "url": f"http://127.0.0.1:{port}/{archive_path.name}",
                                    "hosts": ["127.0.0.1"],
                                    "archive_type": "tar.gz",
                                    "destinations": ["tf/maps"],
                                }
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("ALPHAGSM_TF2_CURATED_MAPS_PATH", str(registry_path))

        server = DummyServer()
        tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
        tf2.command_functions["map"](server, "add", "curated", map_name)
        tf2.command_functions["map"](server, "apply")
    finally:
        httpd.shutdown()

    maps = server.data["maps"]
    assert maps["last_apply"] == "success"
    assert maps["errors"] == []
    installed_bsp = Path(server.data["dir"]) / "tf" / "maps" / f"{map_name}.bsp"
    assert installed_bsp.exists()


def test_map_apply_clears_previous_errors_on_success(tmp_path, monkeypatch):
    """A successful apply wipes out any errors left from a prior failure."""
    map_name = "cp_cleartest"
    bsp_path = _make_bsp_archive(tmp_path, f"{map_name}.bsp")

    httpd, port, _thread = _start_local_http_server(tmp_path)
    try:
        registry_path = _make_registry_json(tmp_path, port, map_name, bsp_path.name)
        monkeypatch.setenv("ALPHAGSM_TF2_CURATED_MAPS_PATH", str(registry_path))

        server = DummyServer()
        tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
        server.data["maps"]["errors"] = ["old error"]
        tf2.command_functions["map"](server, "add", "curated", map_name)
        tf2.command_functions["map"](server, "apply")
    finally:
        httpd.shutdown()

    assert server.data["maps"]["errors"] == []
    assert server.data["maps"]["last_apply"] == "success"


def test_map_apply_monkeypatched_download(tmp_path, monkeypatch):
    """apply_configured_maps can install a curated map when download is patched."""
    bsp_source = tmp_path / "fake.bsp"
    bsp_source.write_bytes(b"VBSP" + b"\x00" * 16)

    registry_path = tmp_path / "curated_maps.json"
    map_name = "cp_granary_pro_rc8"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    map_name: {
                        "default": "current",
                        "releases": {
                            "current": {
                                "url": "http://127.0.0.1/cp_granary_pro_rc8.bsp",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "bsp",
                                "destinations": ["tf/maps"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_TF2_CURATED_MAPS_PATH", str(registry_path))
    monkeypatch.setattr(
        tf2_maps,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            bsp_source, target_path
        ),
    )

    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    tf2.command_functions["map"](server, "add", "curated", map_name)
    tf2.command_functions["map"](server, "apply")

    installed_bsp = Path(server.data["dir"]) / "tf" / "maps" / f"{map_name}.bsp"
    assert installed_bsp.exists()
    assert server.data["maps"]["installed"][0]["resolved_id"] == f"{map_name}.current"
