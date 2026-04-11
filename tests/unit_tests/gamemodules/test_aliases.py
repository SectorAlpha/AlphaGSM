import gamemodules.csgo as csgo
import gamemodules.counterstrike2 as counterstrike2
import gamemodules.cs2server as cs2server
import gamemodules.csgoserver as csgoserver
import gamemodules.minecraft.DEFAULT as minecraft_default
import gamemodules.risingstorm2vietnam as risingstorm2vietnam
import gamemodules.terraria.DEFAULT as terraria_default
import gamemodules.tf2 as tf2
import gamemodules.tf2server as tf2server
import gamemodules.arma3.DEFAULT as arma3_default


def test_alias_modules_point_to_expected_targets():
    assert csgo.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert not hasattr(counterstrike2, "ALIAS_TARGET")
    assert cs2server.ALIAS_TARGET == "counterstrike2"
    assert cs2server._ALIAS_MODULE is counterstrike2
    assert csgoserver.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert risingstorm2vietnam.ALIAS_TARGET == "rs2server"
    assert tf2.ALIAS_TARGET == "teamfortress2"
    assert tf2server.ALIAS_TARGET == "teamfortress2"
    assert minecraft_default.ALIAS_TARGET == "minecraft.vanilla"
    assert terraria_default.ALIAS_TARGET == "terraria.vanilla"
    assert arma3_default.ALIAS_TARGET == "arma3.vanilla"


def test_cs2server_passthroughs_to_counterstrike2(monkeypatch):
    runtime_calls = []
    container_calls = []

    monkeypatch.setattr(
        counterstrike2,
        "get_runtime_requirements",
        lambda server: runtime_calls.append(server) or {"engine": "docker", "family": "steamcmd-linux"},
    )
    monkeypatch.setattr(
        counterstrike2,
        "get_container_spec",
        lambda server: container_calls.append(server) or {"command": ["./game/cs2.sh"]},
    )

    server = object()

    assert cs2server.get_runtime_requirements(server) == {
        "engine": "docker",
        "family": "steamcmd-linux",
    }
    assert cs2server.get_container_spec(server) == {"command": ["./game/cs2.sh"]}
    assert runtime_calls == [server]
    assert container_calls == [server]
