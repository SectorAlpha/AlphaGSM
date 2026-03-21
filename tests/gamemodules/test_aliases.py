import gamemodules.csgo as csgo
import gamemodules.minecraft.DEFAULT as minecraft_default
import gamemodules.terraria.DEFAULT as terraria_default
import gamemodules.tf2 as tf2


def test_alias_modules_point_to_expected_targets():
    assert csgo.ALIAS_TARGET == "counterstrikeglobaloffensive"
    assert tf2.ALIAS_TARGET == "teamfortress2"
    assert minecraft_default.ALIAS_TARGET == "minecraft.vanilla"
    assert terraria_default.ALIAS_TARGET == "terraria.vanilla"
