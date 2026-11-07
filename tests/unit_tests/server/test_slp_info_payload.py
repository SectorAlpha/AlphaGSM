"""SLP info JSON includes the lifecycle runner's required fields."""

import json
import sys
import types

import server.server as server_module
from tests.unit_tests.server.test_server import DummyData, make_server


def test_slp_info_payload_adds_lifecycle_fields_without_dropping_slp_keys():
    """A normal SLP result gains name, map, players, and max_players."""

    source = {
        "description": "A test server",
        "players_online": 2,
        "players_max": 10,
        "version": "1.20.4",
        "player_names": ["Alice", "Bob"],
    }

    payload = server_module._slp_info_payload(source)

    assert payload is not source
    assert payload["name"] == "A test server"
    assert payload["map"] is None
    assert payload["players"] == 2
    assert payload["max_players"] == 10
    assert payload["description"] == "A test server"
    assert payload["players_online"] == 2
    assert payload["players_max"] == 10
    assert payload["version"] == "1.20.4"
    assert payload["player_names"] == ["Alice", "Bob"]
    assert "name" not in source
    assert "map" not in source
    assert "players" not in source
    assert "max_players" not in source


def test_slp_info_payload_keeps_empty_description_as_name():
    """An empty MOTD stays a string name, and a missing MOTD is an empty string."""

    empty = server_module._slp_info_payload({
        "description": "",
        "players_online": 0,
        "players_max": 20,
        "version": "1.21",
    })
    missing = server_module._slp_info_payload({
        "players_online": 1,
        "players_max": 2,
        "version": "1.21",
    })
    coerced = server_module._slp_info_payload({
        "description": 12,
        "players_online": 1,
        "players_max": 2,
    })

    assert empty["name"] == ""
    assert empty["players"] == 0
    assert empty["max_players"] == 20
    assert empty["map"] is None
    assert missing["name"] == ""
    assert coerced["name"] == "12"
    assert isinstance(coerced["name"], str)


def test_slp_info_payload_does_not_replace_existing_fields():
    """Present name, players, max_players, and map values are left alone."""

    source = {
        "description": "MOTD",
        "name": "",
        "players_online": 4,
        "players": False,
        "players_max": 8,
        "max_players": 0,
        "map": "",
        "version": "1.21",
        "player_names": ["Cara"],
    }

    payload = server_module._slp_info_payload(source)

    assert payload["name"] == ""
    assert payload["players"] is False
    assert payload["max_players"] == 0
    assert payload["map"] == ""
    assert payload["description"] == "MOTD"
    assert payload["players_online"] == 4
    assert payload["players_max"] == 8
    assert payload["version"] == "1.21"
    assert payload["player_names"] == ["Cara"]


def test_slp_info_payload_copies_only_real_ints_for_player_counts():
    """Bools and other non-ints do not become players or max_players."""

    flags = server_module._slp_info_payload({
        "description": "Lobby",
        "players_online": True,
        "players_max": False,
        "version": "1.20",
    })
    mixed = server_module._slp_info_payload({
        "description": "Lobby",
        "players_online": "2",
        "players_max": 10,
        "version": "1.20",
    })

    assert "players" not in flags
    assert "max_players" not in flags
    assert flags["players_online"] is True
    assert flags["players_max"] is False
    assert flags["map"] is None
    assert "players" not in mixed
    assert mixed["max_players"] == 10
    assert mixed["players_max"] == 10


def test_info_json_slp_uses_lifecycle_fields(monkeypatch, capsys):
    """info --json publishes the helper fields and keeps the original SLP keys."""

    import utils.query as _ensure_imported  # noqa: F401
    import utils

    srv = make_server(data=DummyData({"port": 25565, "module": "minecraft.vanilla"}))
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.slp_info = lambda host, port, timeout=5.0: {
        "description": "A test server",
        "players_online": 3,
        "players_max": 20,
        "version": "1.20.4",
        "player_names": ["Ada"],
    }
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(
        srv.module,
        "get_info_address",
        lambda server: ("127.0.0.1", 25565, "slp"),
        raising=False,
    )

    srv.info(as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload["protocol"] == "slp"
    assert payload["port"] == 25565
    assert payload["name"] == "A test server"
    assert payload["map"] is None
    assert payload["players"] == 3
    assert payload["max_players"] == 20
    assert payload["description"] == "A test server"
    assert payload["players_online"] == 3
    assert payload["players_max"] == 20
    assert payload["version"] == "1.20.4"
    assert payload["player_names"] == ["Ada"]


def test_info_text_slp_stays_on_original_keys(monkeypatch, capsys):
    """The human-readable SLP print still uses description and the raw counts."""

    import utils.query as _ensure_imported  # noqa: F401
    import utils

    srv = make_server(data=DummyData({"port": 25565, "module": "minecraft.vanilla"}))
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.slp_info = lambda host, port, timeout=5.0: {
        "description": "A test server",
        "players_online": 2,
        "players_max": 10,
        "version": "1.20.4",
    }
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(
        srv.module,
        "get_info_address",
        lambda server: ("127.0.0.1", 25565, "slp"),
        raising=False,
    )

    srv.info()

    out = capsys.readouterr().out
    assert "Server info (SLP on port 25565):" in out
    assert "Description : A test server" in out
    assert "Players     : 2/10" in out
    assert "Version     : 1.20.4" in out
    assert "Map" not in out
