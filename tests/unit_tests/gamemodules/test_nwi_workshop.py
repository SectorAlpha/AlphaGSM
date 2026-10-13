"""Native Insurgency and Day of Infamy server Workshop activation."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport import workshop


@pytest.fixture(params=[("insserver", 222880, "insurgency"), ("doiserver", 447820, "doi")])
def adapter(request, tmp_path, monkeypatch):
    name, app_id, game_dir = request.param
    module = importlib.import_module(f"gamemodules.{name}")
    server = SimpleNamespace(name=f"workshop-{name}", data={})
    module.configure(server, ask=False, port=27015, dir=str(tmp_path))
    def metadata(method, ids, key):
        del key
        if method == "GetCollectionDetails":
            return {str(item): {"result": 1, "children": [{"publishedfileid": "123"}, {"publishedfileid": "124"}]} for item in ids}
        return {str(item): {"result": 1, "consumer_app_id": app_id,
                           "file_type": 2 if str(item) == "900" else 0} for item in ids}
    monkeypatch.setattr(workshop, "_post_details", metadata)
    return module, server, app_id, game_dir


def test_item_url_collection_share_native_list_and_preserve_operator_ids(adapter):
    module, server, app_id, game_dir = adapter
    path = Path(server.data["dir"]) / game_dir / "subscribed_file_ids.txt"
    path.parent.mkdir(exist_ok=True)
    path.write_text("// operator content\n777\n")
    mod = module.command_functions["mod"]
    mod(server, "add", "workshop", "https://steamcommunity.com/sharedfiles/filedetails/?id=123")
    mod(server, "add", "workshop-collection", "900")
    mod(server, "apply")
    assert module.workshop_app_id == app_id
    assert path.read_text() == "// operator content\n777\n123\n124\n"
    assert server.data["mods"]["native_workshop"]["status"] == "configured"
    mod(server, "cleanup")
    assert path.read_text() == "// operator content\n777\n"


def test_wrong_game_and_symlink_config_fail_without_activation(adapter, monkeypatch, tmp_path):
    module, server, _, game_dir = adapter
    mod = module.command_functions["mod"]
    monkeypatch.setattr(workshop, "_post_details", lambda method, ids, key: {str(item): {"result": 1, "consumer_app_id": 550, "file_type": 0} for item in ids})
    with pytest.raises(ServerError, match="belongs"):
        mod(server, "add", "workshop", "123")
    assert server.data["mods"]["desired"]["workshop"] == []
    server.data["mods"]["desired"]["workshop"] = [{"workshop_id": "123"}]
    monkeypatch.setattr(workshop, "_post_details", lambda method, ids, key: {str(item): {"result": 1, "consumer_app_id": module.workshop_app_id, "file_type": 0} for item in ids})
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / game_dir).symlink_to(outside)
    with pytest.raises(ServerError, match="symlink"):
        mod(server, "apply")
    assert not list(outside.iterdir())


def test_native_launch_needs_no_key_and_cleanup_keeps_operator_activation(adapter, monkeypatch):
    module, server, _, game_dir = adapter
    monkeypatch.setattr(module.MODULE, "get_start_command", lambda instance: (["./srcds_run", "-game", game_dir], server.data["dir"]))
    mod = module.command_functions["mod"]
    mod(server, "add", "workshop", "123")
    mod(server, "apply")
    command, _ = module.get_start_command(server)
    assert "-workshop" in command
    assert "+sv_workshop_enabled" in command
    assert not any("authkey" in value or "steamaccount" in value for value in command)
    mod(server, "cleanup")
    command, _ = module.get_start_command(server)
    assert "-workshop" not in command
    path = Path(server.data["dir"]) / game_dir / "subscribed_file_ids.txt"
    path.write_text("777\n")
    command, _ = module.get_start_command(server)
    assert "-workshop" in command


def test_prestart_applies_native_configuration_and_existing_addons(adapter, monkeypatch):
    module, server, _, game_dir = adapter
    module.command_functions["mod"](server, "add", "workshop", "123")
    calls = []
    monkeypatch.setattr(module.MODULE, "prestart", lambda instance: calls.append("valve"))
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda instance: calls.append("addons"))
    module.prestart(server)
    assert calls == ["valve", "addons"]
    assert (Path(server.data["dir"]) / game_dir / "subscribed_file_ids.txt").read_text() == "123\n"
    server.data["mods"]["autoapply"] = False
    calls.clear()
    module.prestart(server)
    assert calls == ["valve"]


def test_engine_probe_rejects_stale_quoted_wrong_game_and_prefix_matches():
    from tests.smoke_tests.nwi_workshop import assert_native_mounts
    good = "BEGIN-nonce\n/srv/server/steamapps/workshop/content/222880/123/maps\nEND-nonce"
    assert_native_mounts(good, 222880, ["123"], "nonce")
    for text in (good.replace("BEGIN-nonce", 'echo "BEGIN-nonce"'),
                 good.replace("/123/", "/1234/"), good.replace("222880", "447820"),
                 good.replace("END-nonce", ""), good.replace("nonce", "old")):
        with pytest.raises(AssertionError):
            assert_native_mounts(text, 222880, ["123"], "nonce")
