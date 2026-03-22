import gamemodules.csgo as csgo
import gamemodules.counterstrike2 as counterstrike2
import gamemodules.cs2server as cs2server
import gamemodules.minecraft.DEFAULT as minecraft_default
import gamemodules.risingstorm2vietnam as risingstorm2vietnam
import gamemodules.terraria.DEFAULT as terraria_default
import gamemodules.tf2 as tf2


def test_alias_modules_point_to_expected_targets():
    assert csgo.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert counterstrike2.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert cs2server.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert risingstorm2vietnam.ALIAS_TARGET == "rs2server"
    assert tf2.ALIAS_TARGET == "teamfortress2"
    assert minecraft_default.ALIAS_TARGET == "minecraft.vanilla"
    assert terraria_default.ALIAS_TARGET == "terraria.vanilla"
