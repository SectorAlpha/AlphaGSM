"""Robust Toolbox status payloads use AlphaGSM's player-cap field."""

import server.server as server_module


class _Query:
    """Return one Space Station 14 status document and an empty info document."""

    class QueryError(Exception):
        """Match the query helper's expected error type."""

    def http_json(self, host, port, path, timeout=10.0):
        del host, port, timeout
        if path == "/status":
            return {
                "name": "Station",
                "players": 0,
                "map": None,
                "soft_max_players": 30,
            }
        if path == "/info":
            return {}
        raise self.QueryError(path)


def test_robust_status_publishes_soft_max_players_as_max_players():
    """A live Robust /status document has soft_max_players and no max_players."""

    _host, payload = server_module._query_robust_status_payload(
        _Query(),
        "127.0.0.1",
        1212,
    )

    assert payload["max_players"] == 30
    assert payload["soft_max_players"] == 30
    assert payload["players"] == 0
