"""Tests for shared Source-game addon mod support."""

import importlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

from gamemodules import gmodserver, hl2dmserver, insserver, l4d2server
from server.modsupport import source_addons
import pytest


THIN_SOURCE_MODULES = [
    "ahl2server",
    "bb2server",
    "bmdmserver",
    "bsserver",
    "ccserver",
    "cssserver",
    "dabserver",
    "doiserver",
    "dodsserver",
    "dysserver",
    "emserver",
    "fofserver",
    "hldmsserver",
    "iosserver",
    "l4dserver",
    "ndserver",
    "nmrihserver",
    "pvkiiserver",
    "sfcserver",
    "zmrserver",
    "zpsserver",
]


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name):
        self.name = name
        self.data = DummyData()


def test_l4d2_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer("l4d2mods")

    l4d2server.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["url"] == []
    assert server.data["mods"]["desired"]["gamebanana"] == []
    assert server.data["mods"]["desired"]["moddb"] == []


def test_l4d2_mod_add_manifest_persists_resolved_entry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "metamod": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/metamod.tar.gz",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "tar.gz",
                                "destinations": ["addons", "cfg"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_L4D2_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer("l4d2mods")
    l4d2server.configure(server, ask=False, port=27015, dir=str(tmp_path))

    l4d2server.command_functions["mod"](server, "add", "manifest", "metamod")

    assert server.data["mods"]["desired"]["curated"][0]["resolved_id"] == "metamod.stable"


def test_l4d2_mod_add_url_accepts_vpk(tmp_path):
    server = DummyServer("l4d2mods")
    l4d2server.configure(server, ask=False, port=27015, dir=str(tmp_path))

    l4d2server.command_functions["mod"](
        server,
        "add",
        "url",
        "https://mods.example.invalid/custom-campaign.vpk",
    )

    entry = server.data["mods"]["desired"]["url"][0]
    assert entry["filename"] == "custom-campaign.vpk"
    assert entry["archive_type"] == "single"


def test_l4d2_mod_apply_installs_gamebanana_archive(tmp_path, monkeypatch):
    server = DummyServer("l4d2mods")
    l4d2server.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    addon_dir = archive_root / "left4dead2" / "addons"
    addon_dir.mkdir(parents=True)
    (addon_dir / "campaign.vpk").write_text("vpk-data", encoding="utf-8")
    archive_path = tmp_path / "l4d2-addon.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(addon_dir / "campaign.vpk", "left4dead2/addons/campaign.vpk")

    monkeypatch.setattr(
        source_addons,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "l4d2-addon.zip",
        },
    )
    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    l4d2server.command_functions["mod"](server, "add", "gamebanana", "12345")
    l4d2server.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "left4dead2" / "addons" / "campaign.vpk"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "gamebanana.12345.777"


def test_l4d2_mod_apply_installs_curated_archive(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    archive_root = tmp_path / "archive-root"
    addon_dir = archive_root / "addons" / "sourcemod" / "plugins"
    addon_dir.mkdir(parents=True)
    (addon_dir / "base.smx").write_text("plugin", encoding="utf-8")
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
                                "destinations": ["addons", "cfg"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_L4D2_CURATED_MODS_PATH", str(registry_path))
    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    server = DummyServer("l4d2mods")
    l4d2server.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    l4d2server.command_functions["mod"](server, "add", "curated", "sourcemod")
    l4d2server.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"]) / "left4dead2" / "addons" / "sourcemod" / "plugins" / "base.smx"
    )
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "sourcemod.stable"


def test_gmod_mod_add_moddb_persists_entry(tmp_path, monkeypatch):
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path))
    monkeypatch.setattr(
        source_addons,
        "resolve_moddb_entry",
        lambda page_url: {
            "source_type": "moddb",
            "requested_id": page_url,
            "resolved_id": "moddb.downloads.308604",
            "download_url": "https://www.moddb.com/downloads/start/308604",
            "archive_type": "zip",
            "filename": "gmod-addon.zip",
        },
    )

    gmodserver.command_functions["mod"](
        server,
        "add",
        "moddb",
        "https://www.moddb.com/mods/gmod-addon-pack/downloads/gmod-addon-pack",
    )

    assert server.data["mods"]["desired"]["moddb"][0]["resolved_id"] == "moddb.downloads.308604"


def test_gmod_mod_apply_installs_direct_gma_url(tmp_path, monkeypatch):
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    gma_path = tmp_path / "example-addon.gma"
    gma_path.write_text("gma-data", encoding="utf-8")

    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            gma_path, target_path
        ),
    )

    gmodserver.command_functions["mod"](
        server,
        "add",
        "url",
        "https://addons.example.invalid/example-addon.gma",
    )
    gmodserver.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "garrysmod" / "addons" / "example-addon.gma"
    assert installed_file.read_text(encoding="utf-8") == "gma-data"


def test_gmod_mod_apply_installs_direct_archive_with_bare_addon_root(tmp_path, monkeypatch):
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    archive_root.mkdir()
    (archive_root / "addon.json").write_text('{"title": "ULX"}', encoding="utf-8")
    bare_lua_dir = archive_root / "lua" / "ulx"
    bare_lua_dir.mkdir(parents=True)
    (bare_lua_dir / "init.lua").write_text("print('ulx')", encoding="utf-8")
    archive_path = tmp_path / "ulx.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(archive_root / "addon.json", "addon.json")
        zf.write(bare_lua_dir / "init.lua", "lua/ulx/init.lua")

    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    gmodserver.command_functions["mod"](
        server,
        "add",
        "url",
        "https://addons.example.invalid/ulx.zip",
    )
    gmodserver.command_functions["mod"](server, "apply")

    installed_file = (
        Path(server.data["dir"]) / "garrysmod" / "addons" / "ulx" / "lua" / "ulx" / "init.lua"
    )
    assert installed_file.read_text(encoding="utf-8") == "print('ulx')"


def test_gmod_mod_cleanup_removes_only_tracked_files(tmp_path):
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))

    tracked_file = Path(server.data["dir"]) / "garrysmod" / "addons" / "tracked.gma"
    manual_file = Path(server.data["dir"]) / "garrysmod" / "addons" / "manual.gma"
    tracked_file.parent.mkdir(parents=True)
    tracked_file.write_text("tracked", encoding="utf-8")
    manual_file.write_text("manual", encoding="utf-8")

    server.data["mods"]["installed"] = [
        {
            "source_type": "url",
            "resolved_id": "url.example-addon.gma",
            "installed_files": ["garrysmod/addons/tracked.gma"],
        }
    ]

    gmodserver.command_functions["mod"](server, "cleanup")

    assert not tracked_file.exists()
    assert manual_file.exists()
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "gamebanana": [], "moddb": []}


def test_gmod_mod_add_curated_resolves_from_override_registry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
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
                                "destinations": ["addons", "cfg"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_GMOD_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path))

    gmodserver.command_functions["mod"](server, "add", "curated", "sourcemod")

    assert server.data["mods"]["desired"]["curated"][0]["resolved_id"] == "sourcemod.stable"


def test_gmod_mod_apply_installs_curated_dependency_chain_from_override_registry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "ulib": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/ulib.zip",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "zip",
                                "destinations": ["addons"],
                            }
                        },
                    },
                    "ulx": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "http://127.0.0.1/ulx.zip",
                                "hosts": ["127.0.0.1"],
                                "archive_type": "zip",
                                "destinations": ["addons"],
                                "dependencies": ["ulib"],
                            }
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    ulib_root = tmp_path / "ulib-root"
    ulib_root.mkdir()
    (ulib_root / "addon.json").write_text('{"title": "ULib"}', encoding="utf-8")
    (ulib_root / "lua" / "ulib").mkdir(parents=True)
    (ulib_root / "lua" / "ulib" / "init.lua").write_text("ulib", encoding="utf-8")
    ulib_archive = tmp_path / "ulib.zip"
    with zipfile.ZipFile(ulib_archive, "w") as zf:
        zf.write(ulib_root / "addon.json", "addon.json")
        zf.write(ulib_root / "lua" / "ulib" / "init.lua", "lua/ulib/init.lua")

    ulx_root = tmp_path / "ulx-root"
    ulx_root.mkdir()
    (ulx_root / "addon.json").write_text('{"title": "ULX"}', encoding="utf-8")
    (ulx_root / "lua" / "ulx").mkdir(parents=True)
    (ulx_root / "lua" / "ulx" / "init.lua").write_text("ulx", encoding="utf-8")
    ulx_archive = tmp_path / "ulx.zip"
    with zipfile.ZipFile(ulx_archive, "w") as zf:
        zf.write(ulx_root / "addon.json", "addon.json")
        zf.write(ulx_root / "lua" / "ulx" / "init.lua", "lua/ulx/init.lua")

    monkeypatch.setenv("ALPHAGSM_GMOD_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))

    def _copy_curated_archive(url, *, allowed_hosts, target_path, checksum=None):
        del allowed_hosts, checksum
        if url.endswith("ulib.zip"):
            return shutil.copy2(ulib_archive, target_path)
        return shutil.copy2(ulx_archive, target_path)

    monkeypatch.setattr(source_addons, "download_to_cache", _copy_curated_archive)

    gmodserver.command_functions["mod"](server, "add", "curated", "ulx")
    gmodserver.command_functions["mod"](server, "apply")

    assert (Path(server.data["dir"]) / "garrysmod" / "addons" / "ulib" / "lua" / "ulib" / "init.lua").exists()
    assert (Path(server.data["dir"]) / "garrysmod" / "addons" / "ulx" / "lua" / "ulx" / "init.lua").exists()
    assert [entry["resolved_id"] for entry in server.data["mods"]["installed"]] == [
        "ulib.stable",
        "ulx.stable",
    ]


def test_gmod_mod_apply_installs_curated_single_file_entry_from_override_registry(tmp_path, monkeypatch):
    registry_path = tmp_path / "curated_mods.json"
    registry_path.write_text(
        json.dumps(
            {
                "families": {
                    "advdupe2": {
                        "default": "stable",
                        "releases": {
                            "stable": {
                                "url": "https://github.com/example/advdupe2.gma",
                                "hosts": ["github.com"],
                                "archive_type": "single",
                                "destinations": ["addons"],
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ALPHAGSM_GMOD_CURATED_MODS_PATH", str(registry_path))
    server = DummyServer("gmodmods")
    gmodserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    gma_path = tmp_path / "advdupe2.gma"
    gma_path.write_text("advdupe2-data", encoding="utf-8")

    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            gma_path, target_path
        ),
    )

    gmodserver.command_functions["mod"](server, "add", "curated", "advdupe2")
    gmodserver.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "garrysmod" / "addons" / "advdupe2.gma"
    assert installed_file.read_text(encoding="utf-8") == "advdupe2-data"
    assert [entry["resolved_id"] for entry in server.data["mods"]["installed"]] == [
        "advdupe2.stable"
    ]


@pytest.mark.parametrize(
    ("family", "expected_resolved_ids"),
    [
        ("ulib", ["ulib.2.71"]),
        ("ulx", ["ulib.2.71", "ulx.3.81"]),
        ("advdupe2", ["advdupe2.v20201205"]),
    ],
)
def test_gmod_checked_in_manifest_resolves_verified_addon_family(family, expected_resolved_ids):
    resolved = gmodserver.load_curated_registry().resolve_with_dependencies(family)

    assert [entry.resolved_id for entry in resolved] == expected_resolved_ids


def test_insserver_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer("insmods")

    insserver.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "gamebanana": [], "moddb": []}


def test_insserver_mod_apply_installs_direct_archive_url(tmp_path, monkeypatch):
    server = DummyServer("insmods")
    insserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))
    archive_root = tmp_path / "archive-root"
    addon_dir = archive_root / "insurgency" / "addons" / "sourcemod"
    addon_dir.mkdir(parents=True)
    (addon_dir / "plugin.vdf").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "ins-addon.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(addon_dir / "plugin.vdf", "insurgency/addons/sourcemod/plugin.vdf")

    monkeypatch.setattr(
        source_addons,
        "download_to_cache",
        lambda url, *, allowed_hosts, target_path, checksum=None: shutil.copy2(
            archive_path, target_path
        ),
    )

    insserver.command_functions["mod"](
        server,
        "add",
        "url",
        "https://mods.example.invalid/ins-addon.zip",
    )
    insserver.command_functions["mod"](server, "apply")

    installed_file = Path(server.data["dir"]) / "insurgency" / "addons" / "sourcemod" / "plugin.vdf"
    assert installed_file.exists()
    assert server.data["mods"]["installed"][0]["source_type"] == "url"


def test_hl2dm_mod_add_gamebanana_persists_entry(tmp_path, monkeypatch):
    server = DummyServer("hl2dmmods")
    hl2dmserver.configure(server, ask=False, port=27015, dir=str(tmp_path))
    monkeypatch.setattr(
        source_addons,
        "resolve_gamebanana_mod",
        lambda item_id: {
            "source_type": "gamebanana",
            "requested_id": item_id,
            "resolved_id": f"gamebanana.{item_id}.777",
            "download_url": "https://gamebanana.com/dl/777",
            "archive_type": "zip",
            "filename": "hl2dm-addon.zip",
        },
    )

    hl2dmserver.command_functions["mod"](server, "add", "gamebanana", "12345")

    assert server.data["mods"]["desired"]["gamebanana"][0]["resolved_id"] == "gamebanana.12345.777"


def test_hl2dm_mod_cleanup_removes_only_tracked_files(tmp_path):
    server = DummyServer("hl2dmmods")
    hl2dmserver.configure(server, ask=False, port=27015, dir=str(tmp_path / "server-root"))

    tracked_file = Path(server.data["dir"]) / "hl2mp" / "addons" / "tracked.vdf"
    manual_file = Path(server.data["dir"]) / "hl2mp" / "addons" / "manual.vdf"
    tracked_file.parent.mkdir(parents=True)
    tracked_file.write_text("tracked", encoding="utf-8")
    manual_file.write_text("manual", encoding="utf-8")
    server.data["mods"]["installed"] = [
        {
            "source_type": "gamebanana",
            "resolved_id": "gamebanana.12345.777",
            "installed_files": ["hl2mp/addons/tracked.vdf"],
        }
    ]

    hl2dmserver.command_functions["mod"](server, "cleanup")

    assert not tracked_file.exists()
    assert manual_file.exists()
    assert server.data["mods"]["desired"] == {"curated": [], "url": [], "gamebanana": [], "moddb": []}


@pytest.mark.parametrize("module_name", THIN_SOURCE_MODULES)
def test_thin_source_wrappers_seed_shared_mod_state(tmp_path, module_name):
    module = importlib.import_module(f"gamemodules.{module_name}")
    server = DummyServer(module_name)

    module.configure(server, ask=False, port=27015, dir=str(tmp_path / module_name))

    assert "mod" in module.command_functions
    assert server.data["mods"]["desired"] == {
        "curated": [],
        "url": [],
        "gamebanana": [],
        "moddb": [],
    }