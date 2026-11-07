"""ARK's early A2S envelope must not count as a loaded game world."""
import pytest

from tests.integration_tests.ark_workshop_helpers import wait_for_loaded_world


def test_world_readiness_rejects_empty_startup_map_and_capacity():
    responses = iter([{"map": "", "max_players": 0}, {"map": "TheIsland", "max_players": 0},
                      {"map": "TheIsland", "max_players": 70}])
    elapsed = [0]
    def pause(seconds):
        elapsed[0] += seconds
    result = wait_for_loaded_world(lambda _remaining: next(responses), 10,
                                   clock=lambda: elapsed[0], sleep=pause)
    assert result["map"] == "TheIsland" and result["max_players"] == 70
    assert elapsed[0] > 0


def test_empty_world_readiness_timeout_fails_instead_of_skipping():
    elapsed = [0]
    def pause(seconds):
        elapsed[0] += seconds
    with pytest.raises(pytest.fail.Exception, match="loaded world"):
        wait_for_loaded_world(lambda _remaining: {"map": "", "max_players": 0}, 3,
                              clock=lambda: elapsed[0], sleep=pause)
