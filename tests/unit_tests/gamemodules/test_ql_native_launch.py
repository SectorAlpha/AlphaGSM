"""Quake Live uses its Steam-era startup, config and query contracts."""

from types import SimpleNamespace

import pytest

from gamemodules import qlserver


@pytest.mark.parametrize("config,game", [("baseq3/server.cfg", "baseq3"),
                                        ("server.cfg", "baseq3"),
                                        ("custommod/match.cfg", "custommod")])
def test_native_launch_selects_game_config_and_startup_factory(tmp_path, config, game):
    (tmp_path / "qzeroded.x64").touch()
    server = SimpleNamespace(name="quake", data={
        "dir": str(tmp_path), "exe_name": "qzeroded.x64", "port": 27960,
        "hostname": "Fixture", "servercfg": config, "startmap": "campgrounds",
        "factory": "ca",
    })
    qlserver.sync_server_config(server)
    for command in (qlserver.get_start_command(server)[0], qlserver.get_container_spec(server)["command"]):
        assert command[command.index("+exec") + 1] == config.split("/")[-1]
        assert command[command.index("fs_game") + 1] == game
        assert command[command.index("net_ip") + 1] == "0.0.0.0"
        assert command[command.index("serverstartup") + 1] == "map campgrounds ca"
        assert "+map" not in command
    text = (tmp_path / game / config.split("/")[-1]).read_text()
    assert 'set sv_hostname "Fixture"' in text
    assert 'set serverstartup "map campgrounds ca"' in text
    assert 'set net_ip "0.0.0.0"' in text


def test_steam_queries_use_a2s_on_runtime_host(monkeypatch):
    server = SimpleNamespace(data={"port": 27960})
    monkeypatch.setattr(qlserver.runtime_module, "resolve_query_host", lambda _server: "172.18.0.1")
    assert qlserver.get_query_address(server) == ("172.18.0.1", 27960, "a2s")
    assert qlserver.get_info_address(server) == ("172.18.0.1", 27960, "a2s")


def test_custom_bind_address_is_applied_before_config_exec(tmp_path):
    server = SimpleNamespace(data={"dir": str(tmp_path), "exe_name": "qzeroded.x64",
                                  "servercfg": "baseq3/match.cfg", "bindaddress": "192.0.2.5"})
    command = qlserver.get_container_spec(server)["command"]
    assert command[command.index("net_ip") + 1] == "192.0.2.5"


@pytest.mark.parametrize("key", ["map", "factory"])
@pytest.mark.parametrize("value", ["asylum;quit", "asylum\nquit", "asylum ca"])
def test_startup_settings_reject_extra_commands(key, value):
    with pytest.raises(qlserver.ServerError, match="Map and factory"):
        qlserver.checkvalue(SimpleNamespace(), [key], value)


def test_config_sync_preserves_operator_settings_and_replaces_duplicate_managed_values(tmp_path):
    config = tmp_path / "baseq3" / "server.cfg"
    config.parent.mkdir()
    config.write_text('// my rules\nset sv_hostname "old"\nseta sv_hostname "also old"\n'
                      'set g_inactivity "120"\nhostname="legacy"\nstartmap=legacy\n'
                      'set serverstartup "startRandomMap"')
    server = SimpleNamespace(name="quake", data={"dir": str(tmp_path), "hostname": "My Server",
                                               "startmap": "asylum", "factory": "duel"})
    qlserver.sync_server_config(server)
    first = config.read_text()
    qlserver.sync_server_config(server)
    assert config.read_text() == first
    assert first.count("sv_hostname") == 1
    assert first.count("serverstartup") == 1
    assert 'set serverstartup "map asylum duel"' in first
    assert '// my rules\nset g_inactivity "120"\n' in first
    assert "legacy" not in first
