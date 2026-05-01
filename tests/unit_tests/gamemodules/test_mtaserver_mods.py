"""Unit tests for mtaserver mod/resource management."""

import io
from pathlib import Path
import json
import shutil
import sys
from unittest.mock import MagicMock, patch

import pytest


sys.modules.pop("gamemodules.mtaserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.archive_install": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
    },
):
    import gamemodules.mtaserver as mod
    import gamemodules.mtaserver.main as mod_main
    from server import ServerError
    from server.modsupport.errors import ModSupportError


class DummyData(dict):
    def save(self):
        return None


class DummyServer:
    def __init__(self, name="mtamods"):
        self.name = name
        self.data = DummyData()


def _configure_server(server, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_main,
        "resolve_download",
        lambda version=None: ("1.6", "https://example.com/mta.tar.gz"),
    )
    mod.configure(server, ask=False, port=22003, dir=str(tmp_path))


def test_mtaserver_configure_seeds_mod_state_defaults(tmp_path, monkeypatch):
    server = DummyServer()

    _configure_server(server, tmp_path, monkeypatch)

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "community": []}


def test_mtaserver_mod_add_manifest_persists_entry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "pattach": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://example.invalid/pAttach.zip",
                                "hosts": ["example.invalid"],
                                "archive_type": "zip",
                                "destinations": ["mods/deathmatch/resources"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_MTASERVER_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    mod.command_functions["mod"](server, "add", "manifest", "pattach")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "pattach"
    assert entry["resolved_id"] == "pattach.stable"
    assert entry["resource_name"] == "pattach"


@pytest.mark.parametrize(
    "family,expected_resolved_id,filename",
    [
        ("pattach", "pattach.v1.2.4", "pAttach-v1.2.4.zip"),
        ("chat2", "chat2.1.0.2", "chat2.zip"),
        ("animationspanel", "animationspanel.1.3", "AnimationsPanel.zip"),
    ],
)
def test_mtaserver_checked_in_manifest_resolves_verified_resource_family(
    family, expected_resolved_id, filename, monkeypatch
):
    monkeypatch.delenv("ALPHAGSM_MTASERVER_CURATED_MODS_PATH", raising=False)

    resolved = mod.load_mta_curated_registry().resolve(family)

    assert resolved.resolved_id == expected_resolved_id
    assert resolved.archive_type == "zip"
    assert list(resolved.hosts) == ["github.com"]
    assert resolved.url.endswith(f"/{filename}")
    assert list(resolved.destinations) == ["mods/deathmatch/resources"]


def test_mtaserver_mod_add_url_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    mod.command_functions["mod"](
        server,
        "add",
        "url",
        "https://resources.example.invalid/myresource.zip",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["requested_id"] == "https://resources.example.invalid/myresource.zip"
    assert entry["archive_type"] == "zip"
    assert entry["resource_name"] == "myresource"


def test_mtaserver_mod_add_url_rejects_invalid_filename(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)

    with pytest.raises(ServerError, match="supported archive filename"):
        mod.command_functions["mod"](
            server,
            "add",
            "url",
            "https://resources.example.invalid/download",
        )


def test_mtaserver_mod_add_community_persists_entry(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path, monkeypatch)
    monkeypatch.setattr(
        mod_main,
        "resolve_mta_community_entry",
        lambda page_url: {
            "source_type": "community",
            "requested_id": page_url,
            "resolved_id": "mtacommunity.19052.fps_by_districtzero_1.0.0",
            "download_page_url": "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052&selectincludes=1",
            "asset_path": "modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&name=fps_by_districtzero.zip",
            "filename": "fps_by_districtzero.zip",
            "archive_type": "zip",
            "resource_name": "fps_by_districtzero",
        },
    )

    mod.command_functions["mod"](
        server,
        "add",
        "community",
        "https://community.multitheftauto.com/?p=resources&s=details&id=19052",
    )

    entry = server.data["mods"]["desired"]["community"][0]
    assert entry["resolved_id"] == "mtacommunity.19052.fps_by_districtzero_1.0.0"
    assert entry["filename"] == "fps_by_districtzero.zip"
    assert entry["resource_name"] == "fps_by_districtzero"


def test_mtaserver_mod_apply_installs_url_archive_with_top_level_resource_dir(tmp_path, monkeypatch):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    archive_root = tmp_path / "archive-root"
    resource_dir = archive_root / "coolrace"
    resource_dir.mkdir(parents=True)
    (resource_dir / "meta.xml").write_text("<meta></meta>", encoding="utf-8")
    (resource_dir / "server.lua").write_text("print('hi')", encoding="utf-8")
    archive_path = tmp_path / "coolrace.zip"

    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(resource_dir / "meta.xml", "coolrace/meta.xml")
        zf.write(resource_dir / "server.lua", "coolrace/server.lua")

    monkeypatch.setattr(
        mod_main,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(archive_path, target_path),
    )

    mod.command_functions["mod"](
        server,
        "add",
        "url",
        "https://resources.example.invalid/coolrace.zip",
    )
    mod.command_functions["mod"](server, "apply")

    installed_root = Path(server.data["dir"]) / "mods" / "deathmatch" / "resources" / "coolrace"
    assert (installed_root / "meta.xml").exists()
    assert (installed_root / "server.lua").exists()


def test_mtaserver_mod_apply_installs_curated_archive_with_root_meta(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "chat2": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://example.invalid/chat2.zip",
                                "hosts": ["example.invalid"],
                                "archive_type": "zip",
                                "destinations": ["mods/deathmatch/resources"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_MTASERVER_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    archive_path = tmp_path / "chat2.zip"

    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("meta.xml", "<meta></meta>")
        zf.writestr("client.lua", "print('client')")
        zf.writestr("server.lua", "print('server')")

    monkeypatch.setattr(
        mod_main,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(archive_path, target_path),
    )

    mod.command_functions["mod"](server, "add", "manifest", "chat2")
    mod.command_functions["mod"](server, "apply")

    installed_root = Path(server.data["dir"]) / "mods" / "deathmatch" / "resources" / "chat2"
    assert (installed_root / "meta.xml").exists()
    assert (installed_root / "client.lua").exists()
    assert (installed_root / "server.lua").exists()


def test_mtaserver_mod_apply_installs_community_archive_and_cleanup_preserves_untracked(
    tmp_path, monkeypatch
):
    server = DummyServer()
    _configure_server(server, tmp_path / "server-root", monkeypatch)
    archive_root = tmp_path / "archive-prefixed"
    resource_dir = archive_root / "mods" / "deathmatch" / "resources" / "fps_by_districtzero"
    resource_dir.mkdir(parents=True)
    (resource_dir / "meta.xml").write_text("<meta></meta>", encoding="utf-8")
    (resource_dir / "client.lua").write_text("print('fps')", encoding="utf-8")
    archive_path = tmp_path / "fps_by_districtzero.zip"

    import zipfile

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(resource_dir / "meta.xml", "mods/deathmatch/resources/fps_by_districtzero/meta.xml")
        zf.write(resource_dir / "client.lua", "mods/deathmatch/resources/fps_by_districtzero/client.lua")

    monkeypatch.setattr(
        mod_main,
        "resolve_mta_community_entry",
        lambda page_url: {
            "source_type": "community",
            "requested_id": page_url,
            "resolved_id": "mtacommunity.19052.fps_by_districtzero_1.0.0",
            "download_page_url": "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052&selectincludes=1",
            "asset_path": "modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&name=fps_by_districtzero.zip",
            "filename": "fps_by_districtzero.zip",
            "archive_type": "zip",
            "resource_name": "fps_by_districtzero",
        },
    )
    monkeypatch.setattr(
        mod_main,
        "download_mta_community_resource",
        lambda download_page_url, asset_path, *, target_path: shutil.copy2(archive_path, target_path),
    )

    mod.command_functions["mod"](
        server,
        "add",
        "community",
        "https://community.multitheftauto.com/?p=resources&s=details&id=19052",
    )
    mod.command_functions["mod"](server, "apply")

    resource_root = Path(server.data["dir"]) / "mods" / "deathmatch" / "resources"
    manual_resource = resource_root / "manualkeep"
    manual_resource.mkdir(parents=True)
    (manual_resource / "meta.xml").write_text("<meta></meta>", encoding="utf-8")
    (manual_resource / "server.lua").write_text("manual", encoding="utf-8")

    mod.command_functions["mod"](server, "cleanup")

    assert not (resource_root / "fps_by_districtzero").exists()
    assert (manual_resource / "meta.xml").exists()
    assert server.data["mods"]["installed"] == []
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "community": []}


def test_download_mta_community_resource_writes_zip_payload(tmp_path, monkeypatch):
    class Response:
        def __init__(self, payload, content_type):
            self._buffer = io.BytesIO(payload)
            self.headers = {"content-type": content_type}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            return self._buffer.read(size)

    responses = iter(
        [
            Response(b"download page", "text/html; charset=utf-8"),
            Response(b"PK\x03\x04zip-bytes", "application/octet-stream"),
        ]
    )

    class Opener:
        def open(self, request, timeout=30):
            del request, timeout
            return next(responses)

    monkeypatch.setattr(mod_main.urllib.request, "build_opener", lambda *args: Opener())

    target_path = tmp_path / "resource.zip"
    mod_main.download_mta_community_resource(
        "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052&selectincludes=1",
        "modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&name=fps_by_districtzero.zip",
        target_path=target_path,
    )

    assert target_path.read_bytes() == b"PK\x03\x04zip-bytes"


def test_download_mta_community_resource_rejects_html_body_with_binary_content_type(tmp_path, monkeypatch):
    class Response:
        def __init__(self, payload, content_type):
            self._buffer = io.BytesIO(payload)
            self.headers = {"content-type": content_type}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            return self._buffer.read(size)

    responses = iter(
        [
            Response(b"download page", "text/html; charset=utf-8"),
            Response(b"<!DOCTYPE html><html><body>Access denied</body></html>", "application/octet-stream"),
        ]
    )

    class Opener:
        def open(self, request, timeout=30):
            del request, timeout
            return next(responses)

    monkeypatch.setattr(mod_main.urllib.request, "build_opener", lambda *args: Opener())

    target_path = tmp_path / "resource.zip"
    with pytest.raises(ModSupportError, match="returned HTML instead of a resource archive"):
        mod_main.download_mta_community_resource(
            "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052&selectincludes=1",
            "modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&name=fps_by_districtzero.zip",
            target_path=target_path,
        )

    assert not target_path.exists()