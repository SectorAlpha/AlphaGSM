"""The name proof shows the website token, waits for the check, and restores the old name."""

import json

import pytest

from agent.prove import QueryBusy, prove_name, temporary_name


def test_long_team_speak_name_is_replaced_by_the_token_and_then_restored(tmp_path):
    token = "SA-" + "a" * 43
    current = "Sector Alpha - ts.sector-alpha.net"
    assert temporary_name(current, token) == token
    assert temporary_name("Voice", token) == "Voice " + token
    names = []
    pending = tmp_path / "prove-name.json"

    def write_name(name):
        names.append(name)

    state = prove_name(
        "ts3",
        token,
        pending_path=pending,
        read_name=lambda: current,
        write_name=write_name,
        request=lambda: {"job_id": "job-1"},
        poll=lambda job_id: {"state": "completed", "verified": True, "job_id": job_id},
        sleep=lambda seconds: None,
        attempts=2,
    )
    assert state["verified"] is True
    assert names == [token, current]
    assert not pending.exists()
    assert token not in json.dumps(names[1])


def test_failure_still_restores_the_previous_name(tmp_path):
    token = "SA-" + "b" * 43
    names = []
    pending = tmp_path / "prove-name.json"

    def request():
        saved = json.loads(pending.read_text())
        assert saved == {"tag": "ts3", "name": "Original"}
        assert token not in pending.read_text()
        raise RuntimeError("offline")

    with pytest.raises(RuntimeError):
        prove_name(
            "ts3",
            token,
            pending_path=pending,
            read_name=lambda: "Original",
            write_name=names.append,
            request=request,
            poll=lambda job_id: {"state": "completed", "verified": False},
            sleep=lambda seconds: None,
        )
    assert names == ["Original " + token, "Original"]
    assert not pending.exists()


def test_interrupted_proof_restores_before_another_attempt(tmp_path):
    token = "SA-" + "c" * 43
    pending = tmp_path / "prove-name.json"
    pending.write_text(json.dumps({"tag": "ts3", "name": "Original"}))
    seen = []
    prove_name(
        "ts3",
        token,
        pending_path=pending,
        read_name=lambda: seen.append("read") or "Original",
        write_name=seen.append,
        request=lambda: {"job_id": "job-1"},
        poll=lambda job_id: {"state": "completed", "verified": True},
        sleep=lambda seconds: None,
    )
    assert seen[0] == "Original"
    with pytest.raises(ValueError, match="other"):
        pending.write_text(json.dumps({"tag": "other", "name": "Kept"}))
        prove_name(
            "ts3",
            token,
            pending_path=pending,
            read_name=lambda: "Original",
            write_name=seen.append,
            request=lambda: {"job_id": "job-1"},
            poll=lambda job_id: {"state": "completed", "verified": True},
            sleep=lambda seconds: None,
        )


def test_busy_query_is_retried_and_the_previous_name_returns(tmp_path):
    token = "SA-" + "d" * 43
    names = []
    calls = {"n": 0}

    def request():
        calls["n"] += 1
        if calls["n"] < 3:
            raise QueryBusy("waiting")
        return {"job_id": "job-1"}

    state = prove_name(
        "ts3",
        token,
        pending_path=tmp_path / "prove-name.json",
        read_name=lambda: "Original",
        write_name=names.append,
        request=request,
        poll=lambda job_id: {"state": "completed", "verified": True},
        sleep=lambda seconds: None,
        request_attempts=4,
    )
    assert state["verified"] is True
    assert calls["n"] == 3
    assert names == ["Original " + token, "Original"]
