"""The public protocol map is anonymous status only and does not load the manager."""

import subprocess
import sys

from server.public_protocols import STRUCTURED, protocol_for, queryable_games


def test_catalogue_covers_anonymous_status_and_refuses_reachability_checks():
    assert protocol_for("minecraft.vanilla") == "slp"
    assert protocol_for("minecraft.paper") == "slp"
    assert protocol_for("minecraft.bedrock") == "bedrock"
    assert protocol_for("teamfortress2") == "a2s"
    assert protocol_for("counterstrike2") == "a2s"
    assert protocol_for("q3server") == "quake"
    assert protocol_for("ts3server") == "ts3"
    assert protocol_for("valheim") is None
    assert protocol_for("wreckfestserver") is None
    assert protocol_for("sevendaystodie") is None
    games = queryable_games()
    assert len(games) > 50
    assert {protocol for _game, protocol, _name in games} <= STRUCTURED
    assert "Team Fortress 2" in {name for _game, _protocol, name in games}
    assert "TeamSpeak 3" in {name for _game, _protocol, name in games}


def test_protocol_map_does_not_import_the_server_manager():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from server.public_protocols import protocol_for; import sys; "
            "assert protocol_for('rust') == 'a2s'; "
            "assert 'server.server' not in sys.modules; assert 'core' not in sys.modules",
        ],
        check=True,
        timeout=20,
    )
