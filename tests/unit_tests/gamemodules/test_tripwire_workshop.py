"""Tripwire native Workshop subscription ownership and operator preservation."""
from importlib import import_module
from copy import deepcopy

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


@pytest.fixture(params=[("kf2server", "KFGame/Config/LinuxServer-KFEngine.ini",
                        "OnlineSubsystemSteamworks.KFWorkshopSteamworks"),
                       ("rs2server", "ROGame/Config/PCServer-ROEngine.ini",
                        "OnlineSubsystemSteamworks.TWWorkshopSteamworks")])
def native_server(request, tmp_path, monkeypatch):
    """Provide native config files with unrelated operator settings."""
    game, relative, section = request.param
    adapter = import_module(f"gamemodules.{game}.workshop")
    if game == "kf2server":
        monkeypatch.setattr(adapter, "IS_LINUX", True)
    shared = import_module("gamemodules.kf2server.workshop")
    server = DummyServer("tripwireworkshop")
    server.data.update(module=game, dir=str(tmp_path))
    config = tmp_path / relative
    config.parent.mkdir(parents=True)
    config.write_text(f"; operator\n[{section}]\nServerSubscribedWorkshopItems=999 // operator map\n"
                      "[IpDrv.TcpNetDriver]\nDownloadManagers=Engine.ChannelDownload\n"
                      "NetServerMaxTickRate=30\n[Other]\nKeep=value\n")
    monkeypatch.setattr(shared.runtime_module, "check_server_running", lambda _server: False)
    return adapter, server, config, section, shared


def test_native_subscriptions_preserve_operator_items_and_prioritize_client_delivery(native_server):
    adapter, server, config, _section, _shared = native_server
    adapter.configure_workshop(server, ["222", "111", "999"])
    text = config.read_text()
    assert "ServerSubscribedWorkshopItems=999 // operator map" in text
    assert text.index("ServerSubscribedWorkshopItems=222") < text.index("ServerSubscribedWorkshopItems=111")
    assert text.index("DownloadManagers=OnlineSubsystemSteamworks.SteamWorkshopDownload") < text.index(
        "DownloadManagers=Engine.ChannelDownload")
    adapter.configure_workshop(server, [])
    text = config.read_text()
    assert "ServerSubscribedWorkshopItems=999 // operator map" in text
    assert "ServerSubscribedWorkshopItems=111" not in text and "ServerSubscribedWorkshopItems=222" not in text
    assert "DownloadManagers=OnlineSubsystemSteamworks.SteamWorkshopDownload" not in text
    assert "NetServerMaxTickRate=30" in text and "Keep=value" in text and "; operator" in text


def test_preexisting_workshop_download_manager_is_never_adopted_or_removed(native_server):
    adapter, server, config, _section, _shared = native_server
    text = config.read_text().replace("NetServerMaxTickRate=30", "DownloadManagers="
                                      "OnlineSubsystemSteamworks.SteamWorkshopDownload // operator\n"
                                      "NetServerMaxTickRate=30")
    config.write_text(text)
    adapter.configure_workshop(server, ["111"])
    adapter.configure_workshop(server, [])
    text = config.read_text()
    assert "DownloadManagers=OnlineSubsystemSteamworks.SteamWorkshopDownload // operator" in text
    assert "DownloadManagers=Engine.ChannelDownload" in text


def test_running_server_refuses_native_config_publication(native_server, monkeypatch):
    adapter, server, config, _section, shared = native_server
    original = config.read_bytes()
    monkeypatch.setattr(shared.runtime_module, "check_server_running", lambda _server: True)
    with pytest.raises(ServerError, match="stop|running"):
        adapter.configure_workshop(server, ["111"])
    assert config.read_bytes() == original and "mods" not in server.data
    assert not (config.parents[1] / "Cache").exists()


def test_empty_unmanaged_state_needs_no_config_or_runtime_mutation(native_server, monkeypatch):
    adapter, server, config, _section, shared = native_server
    original = config.read_bytes()
    monkeypatch.setattr(shared.runtime_module, "check_server_running", lambda _server: True)
    assert adapter.configure_workshop(server, []) == []
    assert config.read_bytes() == original and "mods" not in server.data


def test_native_config_symlink_and_oversize_are_rejected(native_server):
    adapter, server, config, _section, _shared = native_server
    config.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    outside = config.parent / "operator.ini"
    outside.write_text("operator")
    config.unlink()
    config.symlink_to(outside)
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    assert outside.read_text() == "operator"


def test_duplicate_native_sections_are_rejected_before_mutation(native_server):
    adapter, server, config, section, _shared = native_server
    config.write_text(config.read_text() + f"[{section}]\nServerSubscribedWorkshopItems=888\n")
    original = config.read_bytes()
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    assert config.read_bytes() == original


def test_state_save_failure_restores_native_config_and_ownership(native_server, monkeypatch):
    adapter, server, config, _section, _shared = native_server
    adapter.configure_workshop(server, ["111"])
    original, previous = config.read_bytes(), dict(server.data["mods"])
    def fail():
        raise OSError("state disk full")
    monkeypatch.setattr(server.data, "save", fail)
    with pytest.raises(OSError, match="state disk full"):
        adapter.configure_workshop(server, ["222"])
    assert config.read_bytes() == original
    assert server.data["mods"] == previous


def test_kf2_creates_safe_native_cache_for_engine_downloads(native_server):
    adapter, server, config, _section, _shared = native_server
    if server.data["module"] != "kf2server":
        return
    cache = config.parents[1] / "Cache"
    adapter.configure_workshop(server, ["111"])
    assert cache.is_dir()
    adapter.configure_workshop(server, [])
    assert cache.is_dir()
    cache.rmdir()
    outside = config.parent / "operator-cache"
    outside.mkdir()
    cache.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])


@pytest.mark.parametrize("desired", [[], ["222"]], ids=["cleanup", "apply"])
@pytest.mark.parametrize("legacy", [False, True], ids=["exact-state", "legacy-state"])
@pytest.mark.parametrize("key,value,edited", [
    ("ServerSubscribedWorkshopItems", "111", "{key}={value} ; operator edited\n"),
    ("ServerSubscribedWorkshopItems", "111", "+{key}={value}\n"),
    ("ServerSubscribedWorkshopItems", "111", " {key} = {value}\n"),
    ("DownloadManagers", "OnlineSubsystemSteamworks.SteamWorkshopDownload",
     "{key}={value} // operator edited\n"),
    ("DownloadManagers", "OnlineSubsystemSteamworks.SteamWorkshopDownload", "+{key}={value}\n"),
    ("DownloadManagers", "OnlineSubsystemSteamworks.SteamWorkshopDownload", " {key} = {value}\n"),
])
def test_edited_managed_lines_refuse_apply_and_cleanup_before_mutation(
        native_server, desired, legacy, key, value, edited):
    adapter, server, config, _section, _shared = native_server
    adapter.configure_workshop(server, ["111"])
    owner = "kf2_workshop" if server.data["module"] == "kf2server" else "rs2_workshop"
    if legacy:
        server.data["mods"][owner] = {"ids": ["111"], "download_manager_owned": True}
    config.write_text(config.read_text().replace(f"{key}={value}\n", edited.format(key=key, value=value)))
    before, state = config.read_bytes(), deepcopy(server.data)
    cache = config.parents[1] / "Cache"
    if cache.exists():
        cache.rmdir()
    with pytest.raises(ServerError, match="changed|edited|ownership"):
        adapter.configure_workshop(server, desired)
    assert config.read_bytes() == before
    assert server.data == state
    assert not cache.exists()


@pytest.mark.parametrize("desired", [[], ["222"]], ids=["cleanup", "apply"])
def test_legacy_ownership_only_migrates_unchanged_canonical_lines(native_server, desired):
    adapter, server, config, _section, _shared = native_server
    adapter.configure_workshop(server, ["111"])
    owner = "kf2_workshop" if server.data["module"] == "kf2server" else "rs2_workshop"
    server.data["mods"][owner] = {"ids": ["111"], "download_manager_owned": True}
    adapter.configure_workshop(server, desired)
    text = config.read_text()
    assert "ServerSubscribedWorkshopItems=111\n" not in text
    assert "ServerSubscribedWorkshopItems=999 // operator map" in text
    if desired:
        assert "ServerSubscribedWorkshopItems=222\n" in text


def test_unowned_same_id_entries_survive_managed_cleanup(native_server):
    adapter, server, config, _section, _shared = native_server
    adapter.configure_workshop(server, ["111"])
    config.write_text(config.read_text().replace(
        "ServerSubscribedWorkshopItems=111\n",
        "ServerSubscribedWorkshopItems=111\n+ServerSubscribedWorkshopItems=111 // operator\n").replace(
        "DownloadManagers=Engine.ChannelDownload\n",
        "DownloadManagers=OnlineSubsystemSteamworks.SteamWorkshopDownload // operator\n"
        "DownloadManagers=Engine.ChannelDownload\n"))
    adapter.configure_workshop(server, [])
    text = config.read_text()
    assert "+ServerSubscribedWorkshopItems=111 // operator\n" in text
    assert "DownloadManagers=OnlineSubsystemSteamworks.SteamWorkshopDownload // operator\n" in text
    assert "ServerSubscribedWorkshopItems=111\n" not in text
