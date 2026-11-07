"""ARK proof requires an actually initialized native custom world and A2S."""

from types import SimpleNamespace

import pytest

from tests.smoke_tests.ark_workshop import (
    FIXTURE_ID, configured_fixture_map, assert_native_world, assert_workshop_map_info,
)


MAP = f"/Game/Mods/{FIXTURE_ID}/FlatMap"
WORLD = (
    '[2026.10.15-00.00.00:000][  0]Server: "Disposable" has successfully started!\n'
    f'[2026.10.15-00.00.00:001][  0]Commandline:  {MAP}?listen?Port=7777\n'
    '[2026.10.15-00.00.00:002][  0]Full Startup: 12.34 seconds\n'
)


def test_native_initialized_world_and_real_exact_a2s_map_prove_execution():
    assert_native_world(WORLD, MAP)
    assert_workshop_map_info({"protocol": "a2s", "map": "FlatMap", "max_players": 70, "port": 27015}, 27015)
    server = SimpleNamespace(data={"mods": {"ark_workshop_maps": {FIXTURE_ID: {"FlatMap": MAP}}}})
    assert configured_fixture_map(server) == MAP


@pytest.mark.parametrize("native", [
    "", "echo " + WORLD.replace("\n", "\necho "),
    WORLD.replace(MAP, "/Game/Maps/TheIsland"),
    WORLD.replace("has successfully started!", "initializing"),
    WORLD.replace("Full Startup:", "Starting:"),
    f"ActiveMods={FIXTURE_ID}\n?GameModIds={FIXTURE_ID}",
])
def test_download_config_command_echo_or_unfinished_wrong_world_cannot_pass(native):
    with pytest.raises(AssertionError):
        assert_native_world(native, MAP)


@pytest.mark.parametrize("info", [
    {"protocol": "tcp", "map": "FlatMap", "max_players": 70},
    {"protocol": "a2s", "map": "TheIsland", "max_players": 70},
    {"protocol": "a2s", "map": "FlatMap", "max_players": 0},
    {"protocol": "a2s", "map": "FlatMap", "max_players": True},
    {"protocol": "a2s", "map": "", "max_players": 0},
])
def test_startup_protocol_envelope_cannot_substitute_for_workshop_world(info):
    with pytest.raises(AssertionError):
        assert_workshop_map_info(info)


def test_wrong_or_unstaged_fixture_world_is_rejected():
    for maps in ({}, {FIXTURE_ID: {"FlatMap": "/Game/Maps/FlatMap"}},
                 {FIXTURE_ID: {"FlatMap": f"/Game/Mods/{FIXTURE_ID}/Other"}}):
        with pytest.raises(AssertionError):
            configured_fixture_map(SimpleNamespace(data={"mods": {"ark_workshop_maps": maps}}))


def test_custom_world_on_wrong_query_port_cannot_pass():
    with pytest.raises(AssertionError):
        assert_workshop_map_info({"protocol": "a2s", "map": "FlatMap", "max_players": 70,
                                  "port": 27016}, 27015)
