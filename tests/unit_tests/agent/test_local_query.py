"""The agent reads a local server itself and does not upload that observation."""

import pytest

from agent.config import Config
from agent.local_query import observe_local, query_tag
from utils.query import QueryError


def _config(tmp_path):
    cfg = Config(tmp_path / "agent")
    cfg.enroll(
        "https://control.example",
        dict(
            schema_version=1,
            installation_id="install-1",
            credential_generation=1,
            reporting=dict(key_id="report-key", secret="x" * 43),
            management=None,
        ),
    )
    cfg.bind(
        "binding-1",
        "my-server",
        1,
        actions=["status"],
        publication=False,
        metadata=dict(name="game", game_id="counterstrike2", host="game.example", port=27015, capacity=16),
    )
    return cfg


def test_observe_local_uses_the_module_hook_and_the_shared_query(monkeypatch):
    class Module:
        def get_info_address(self, server):
            del server
            return ("10.1.2.3", 27015, "a2s")

    class Local:
        module = Module()
        data = {"port": 27015}

    import server.public_query as public_query

    monkeypatch.setattr(public_query.query, "a2s_info", lambda host, port, timeout=2.0, **kwargs: (host, port))
    monkeypatch.setattr(
        public_query.query,
        "parse_a2s_info",
        lambda raw: dict(name="Dust", map="de_dust2", players=0, max_players=16, bots=4, address=raw),
    )
    result = observe_local(Local(), "counterstrike2")
    assert result == dict(name="Dust", map="de_dust2", players=0, capacity=16)


def test_games_without_an_anonymous_status_query_are_refused():
    with pytest.raises(QueryError, match="no anonymous status query"):
        observe_local(object(), "valheim")


def test_query_command_prints_the_local_result_and_does_not_construct_a_client(tmp_path, monkeypatch, capsys):
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        "agent.local_query.observe_local",
        lambda server, game_id, timeout=5.0: dict(name="Dust", players=1, capacity=16, map="de_dust2"),
    )
    query_tag(cfg, "my-server", open_server=lambda tag: object())
    printed = capsys.readouterr().out
    assert "not sent to Sector Alpha" in printed
    assert "name=Dust" in printed
    assert "players=1/16" in printed
    assert "map=de_dust2" in printed
