import gamemodules.arma3 as arma3
import gamemodules.arma3.altislife as altislife
import gamemodules.arma3.desolationredux as desolationredux
import gamemodules.arma3.epoch as epoch
import gamemodules.arma3.exile as exile
import gamemodules.arma3.headless as headless
import gamemodules.arma3.vanilla as vanilla
import gamemodules.arma3.wasteland as wasteland


def test_arma3_package_reexports_vanilla_module_contract():
    assert arma3.configure is vanilla.configure
    assert arma3.get_start_command is vanilla.get_start_command


def test_arma3_package_variants_point_to_existing_modules():
    assert altislife.get_start_command.__module__ == "gamemodules.arma3altislifeserver"
    assert desolationredux.get_start_command.__module__ == "gamemodules.arma3desolationreduxserver"
    assert epoch.get_start_command.__module__ == "gamemodules.arma3epochserver"
    assert exile.get_start_command.__module__ == "gamemodules.arma3exileserver"
    assert headless.get_start_command.__module__ == "gamemodules.arma3headlessserver"
    assert wasteland.get_start_command.__module__ == "gamemodules.arma3wastelandserver"
