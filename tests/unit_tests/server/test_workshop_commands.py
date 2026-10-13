"""Workshop command intake and install ownership through the Source adapter."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport.errors import ModSupportError
from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport import workshop


@pytest.fixture(autouse=True)
def batch_metadata(monkeypatch):
    """Command tests mock remote metadata; provider tests exercise actual batching."""
    monkeypatch.setattr(workshop, "resolve_workshop_items", lambda ids, app_id: [
        workshop.resolve_workshop_item(identifier, app_id) for identifier in ids
    ])


class Data(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.saved = 0

    def save(self):
        self.saved += 1


def support(tmp_path, downloader=None, **kwargs):
    adapter = build_source_addon_mod_support(
        game_label="L4D2", game_dir="left4dead2", cache_namespace="left4dead2",
        direct_url_suffixes={".vpk": "single"}, direct_url_filename_description="VPK",
        enabled_sources=("workshop",), workshop_app_id=550,
        workshop_downloader_getter=lambda: downloader, **kwargs,
    )
    server = SimpleNamespace(data=Data(dir=str(tmp_path / "server")))
    adapter.ensure_mod_state(server)
    return adapter, server


def valid_item(identifier, app_id):
    assert app_id == 550
    return {"workshop_id": str(identifier), "source_type": "workshop",
            "resolved_id": f"workshop.{identifier}"}


def test_single_item_uses_game_metadata_before_save(tmp_path, monkeypatch):
    adapter, server = support(tmp_path)
    before = copy.deepcopy(server.data)

    def wrong_game(identifier, app_id):
        assert app_id == 550
        raise ModSupportError("belongs to game AppID 730; expected 550")

    monkeypatch.setattr(workshop, "resolve_workshop_item", wrong_game)
    with pytest.raises(ServerError, match="expected 550"):
        adapter.command_functions["mod"](server, "add", "workshop", "123")
    assert server.data == before
    assert server.data.saved == 0


def test_collection_snapshot_deduplicates_and_reimport_adds_new_items(tmp_path, monkeypatch):
    adapter, server = support(tmp_path)
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    children = ["10", "11"]
    monkeypatch.setattr(workshop, "resolve_workshop_collection", lambda identifier, app_id: list(children))
    command = adapter.command_functions["mod"]
    command(server, "add", "workshop", "10")
    command(server, "add", "workshop-collection", "1")
    desired = server.data["mods"]["desired"]["workshop"]
    assert [entry["workshop_id"] for entry in desired] == ["10", "11"]
    assert desired[1]["collection_id"] == "1"
    children[:] = ["11", "12"]
    command(server, "add", "workshop-collection", "1")
    assert [entry["workshop_id"] for entry in desired] == ["10", "11", "12"]


def test_failed_collection_keeps_existing_state_and_does_not_save(tmp_path, monkeypatch):
    adapter, server = support(tmp_path)
    before = copy.deepcopy(server.data)

    def unavailable(identifier, app_id):
        raise ModSupportError("collection unavailable")

    monkeypatch.setattr(workshop, "resolve_workshop_collection", unavailable)
    with pytest.raises(ServerError, match="unavailable"):
        adapter.command_functions["mod"](server, "add", "workshop-collection", "1")
    assert server.data == before
    assert server.data.saved == 0


def test_apply_revalidates_legacy_ids_before_download(tmp_path, monkeypatch):
    def download(*args):
        pytest.fail("Wrong-game entry must not be downloaded")

    adapter, server = support(tmp_path, downloader=download)
    server.data["mods"]["desired"]["workshop"] = [valid_item("10", 550)]

    def wrong_game(*args):
        raise ModSupportError("wrong game")

    monkeypatch.setattr(workshop, "resolve_workshop_item", wrong_game)
    with pytest.raises(ServerError, match="wrong game"):
        adapter.command_functions["mod"](server, "apply")


def test_l4d2_vpk_install_and_remove_only_owned_files(tmp_path, monkeypatch):
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "original.vpk").write_bytes(b"VPK payload")
    calls = []

    def download(path, app_id, item_id, anonymous):
        calls.append((app_id, item_id, anonymous))
        return payload

    adapter, server = support(tmp_path, downloader=download, workshop_single_file_suffix=".vpk")
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    command = adapter.command_functions["mod"]
    command(server, "add", "workshop", "10")
    command(server, "apply")
    installed = Path(server.data["dir"]) / "left4dead2/addons/workshop/10.vpk"
    assert installed.read_bytes() == b"VPK payload"
    assert calls == [(550, "10", True)]
    unrelated = installed.with_name("operator.vpk")
    unrelated.write_bytes(b"owned by operator")
    command(server, "remove", "workshop", "10")
    command(server, "apply")
    assert not installed.exists()
    assert unrelated.exists()


def test_workshop_download_failure_is_recorded(tmp_path, monkeypatch):
    import subprocess

    def failed(*args):
        raise subprocess.CalledProcessError(1, ["steamcmd"], output="Access Denied")

    adapter, server = support(tmp_path, downloader=failed)
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    command = adapter.command_functions["mod"]
    command(server, "add", "workshop", "10")
    with pytest.raises(ServerError, match="Access Denied"):
        command(server, "apply")
    assert "Access Denied" in server.data["mods"]["errors"][0]


def test_partial_collection_failure_preserves_ownership_for_cleanup(tmp_path, monkeypatch):
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.vpk").write_bytes(b"addon")

    def download(path, app_id, item_id, anonymous):
        if item_id == "11":
            raise ModSupportError("second item download failed")
        return payload

    adapter, server = support(tmp_path, downloader=download, workshop_single_file_suffix=".vpk")
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    server.data["mods"]["desired"]["workshop"] = [valid_item("10", 550), valid_item("11", 550)]
    command = adapter.command_functions["mod"]
    with pytest.raises(ServerError, match="second item"):
        command(server, "apply")
    installed = Path(server.data["dir"]) / "left4dead2/addons/workshop/10.vpk"
    assert installed.exists()
    assert server.data["mods"]["installed"][0]["resolved_id"] == "workshop.10"
    command(server, "cleanup")
    assert not installed.exists()


@pytest.mark.parametrize("symlink_level", ["workshop", "game"])
def test_workshop_destination_symlink_rejected_before_overwrite(tmp_path, monkeypatch, symlink_level):
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.vpk").write_bytes(b"addon")
    adapter, server = support(tmp_path, downloader=lambda *a: payload, workshop_single_file_suffix=".vpk")
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    outside = tmp_path / "outside"
    outside.mkdir()
    external = outside / "10.vpk" if symlink_level == "workshop" else outside / "addons/workshop/10.vpk"
    external.parent.mkdir(parents=True, exist_ok=True)
    external.write_bytes(b"operator file")
    addons = Path(server.data["dir"]) / "left4dead2/addons"
    if symlink_level == "workshop":
        addons.mkdir(parents=True)
        (addons / "workshop").symlink_to(outside, target_is_directory=True)
    else:
        addons.parent.parent.mkdir(parents=True)
        addons.parent.symlink_to(outside, target_is_directory=True)
    adapter.command_functions["mod"](server, "add", "workshop", "10")
    with pytest.raises(ServerError):
        adapter.command_functions["mod"](server, "apply")
    assert external.read_bytes() == b"operator file"


def test_cleanup_rejects_replaced_destination_symlink(tmp_path, monkeypatch):
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.vpk").write_bytes(b"addon")
    adapter, server = support(tmp_path, downloader=lambda *a: payload, workshop_single_file_suffix=".vpk")
    monkeypatch.setattr(workshop, "resolve_workshop_item", valid_item)
    command = adapter.command_functions["mod"]
    command(server, "add", "workshop", "10")
    command(server, "apply")
    workshop_dir = Path(server.data["dir"]) / "left4dead2/addons/workshop"
    workshop_dir.rename(workshop_dir.with_name("original"))
    outside = tmp_path / "outside"
    outside.mkdir()
    external = outside / "10.vpk"
    external.write_bytes(b"operator file")
    workshop_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError):
        command(server, "cleanup")
    assert external.read_bytes() == b"operator file"
    assert server.data["mods"]["installed"]


def test_mod_intake_and_remove_accept_workshop_urls(tmp_path, monkeypatch):
    adapter, server = support(tmp_path)
    monkeypatch.setattr(workshop, 'resolve_workshop_item', valid_item)
    monkeypatch.setattr(workshop, 'resolve_workshop_collection', lambda identifier, app_id: ['11'])
    command = adapter.command_functions['mod']
    command(server, 'add', 'workshop', 'https://steamcommunity.com/sharedfiles/filedetails/?id=10')
    command(server, 'add', 'workshop-collection', 'https://steamcommunity.com/sharedfiles/filedetails/?id=1')
    desired = server.data['mods']['desired']['workshop']
    assert [item['workshop_id'] for item in desired] == ['10', '11']
    assert desired[1]['collection_id'] == '1'
    command(server, 'remove', 'workshop', 'https://steamcommunity.com/sharedfiles/filedetails/?id=10')
    assert [item['workshop_id'] for item in desired] == ['11']
