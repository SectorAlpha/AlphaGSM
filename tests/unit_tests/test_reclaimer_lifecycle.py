"""Replay Reclaimer smoke failure cleanup without any real game files."""

import json
from types import SimpleNamespace

import pytest

from tests.smoke_tests import reclaimer_lifecycle as runner
from scripts import select_test_port


@pytest.mark.parametrize("failed_stage", ["start", "stop", "readiness"])
def test_smoke_cleans_partial_launches_and_persistent_stop_failures(tmp_path, monkeypatch, failed_stage):
    monkeypatch.setattr(select_test_port, "pick_free_port_group", lambda count: 25000)
    commands = []

    def run(command, **kwargs):
        action = command[3]
        commands.append(action)
        failed = action == failed_stage or (action == "info" and failed_stage == "readiness")
        info = {"protocol": "reclaimer_rcon", "port": 25001, "players": 0, "max_players": 16, "map": "Guardian"}
        return SimpleNamespace(returncode=1 if failed else 0, stdout=json.dumps(info) if action == "info" else "",
                               stderr="simulated " + failed_stage + " failure" if failed else "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    with pytest.raises(AssertionError):
        runner.run_lifecycle(tmp_path, "/owned-fixture", timeout=0 if failed_stage == "readiness" else 2)
    assert "stop" in commands
    if failed_stage == "stop":
        assert commands[-1] == "kill"


def test_smoke_without_owned_source_is_prerequisite_skip(monkeypatch):
    monkeypatch.delenv("ALPHAGSM_RECLAIMER_ASSETS", raising=False)
    monkeypatch.setattr(runner.sys, "argv", ["reclaimer_lifecycle.py"])
    assert runner.main() == 77
