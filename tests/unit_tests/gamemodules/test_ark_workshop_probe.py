"""ARK proof must execute a complete property command on native RCON."""

from types import SimpleNamespace

import pytest

from tests.smoke_tests.ark_workshop import (
    NATIVE_COMMAND, assert_native_object_property, prepare_probe, probe_native_object,
)


OBJECT = (
    '0) PrimalGameData_BP_Spoilers_C '
    '/Game/Mods/Spoilers/PrimalGameData_BP_Spoilers.Default__PrimalGameData_BP_Spoilers_C.'
    'ModName = "Meat Spoiler"\n'
)


@pytest.mark.parametrize("prefix", ["", "LogObj: ", "[2026.10.14-17.20.00:001][  1]LogObj: "])
def test_native_property_record_accepts_rcon_or_flushed_engine_output(prefix):
    assert_native_object_property(prefix + OBJECT)


@pytest.mark.parametrize("output", [
    "", "Server received command but the command had no response", NATIVE_COMMAND,
    "echo " + OBJECT,
    "LogConsoleResponse: Executing " + NATIVE_COMMAND,
    "LogLinker: Failed to find PrimalGameData_BP_Spoilers_C",
    OBJECT.replace("PrimalGameData_BP_Spoilers_C", "PrimalGameData_BP_C"),
    OBJECT.replace("ModName =", "UnknownProperty ="),
    OBJECT.replace('"Meat Spoiler"', '""'),
    "ActiveMods=2860800256\n?GameModIds=2860800256",
])
def test_echo_receipt_config_and_missing_or_wrong_objects_do_not_prove_native_load(output):
    with pytest.raises(AssertionError, match="native Blueprint ModName"):
        assert_native_object_property(output)


def test_probe_uses_runtime_host_and_authenticated_property_command(monkeypatch):
    from server import runtime
    from utils import query

    server = SimpleNamespace(data={"adminpassword": "private-disposable", "rconport": 27020})
    monkeypatch.setattr(runtime, "resolve_query_host", lambda selected: "172.18.0.1"
                        if selected is server else "wrong")
    requests = []
    def command(host, port, password, timeout, text):
        requests.append((host, port, password, timeout, text))
        return "No Players Connected" if text == "ListPlayers" else OBJECT
    monkeypatch.setattr(query, "_source_rcon_command_once", command)
    probe_native_object(server, read_logs=lambda: (_ for _ in ()).throw(
        AssertionError("Valid RCON proof must not depend on a writable engine log")))
    assert [request[-1] for request in requests] == ["ListPlayers", NATIVE_COMMAND]
    assert all(request[:3] == ("172.18.0.1", 27020, "private-disposable") for request in requests)
    assert NATIVE_COMMAND.endswith(" ModName SHOWDEFAULTS")


def test_generic_rcon_receipt_times_out_with_native_response_and_redacted_password(monkeypatch):
    from server import runtime

    server = SimpleNamespace(data={"adminpassword": "private-disposable", "rconport": 27020})
    monkeypatch.setattr(runtime, "resolve_query_host", lambda _server: "127.0.0.1")
    elapsed = [0]
    def sleep(seconds):
        elapsed[0] += seconds
    def command(text, _remaining):
        return "No Players Connected" if text == "ListPlayers" else "Server received, But no response!!"
    with pytest.raises(AssertionError, match="But no response") as failure:
        probe_native_object(server, timeout=3, command=command,
                            read_logs=lambda: "private-disposable", clock=lambda: elapsed[0], sleep=sleep)
    assert "private-disposable" not in str(failure.value)


def test_prepare_keeps_generated_password_out_of_argv_and_avoids_claimed_ports(monkeypatch):
    from scripts import select_test_port

    requests = []
    ports = iter((7777, 7778, 27015, 27020))
    monkeypatch.setattr(select_test_port, "pick_free_port_group", lambda _count: next(ports))
    server = SimpleNamespace(data={"port": 7777, "queryport": 27015},
                             doset=lambda *args: requests.append(args))
    prepare_probe(server)
    assert requests[0][0] == "adminpassword" and len(requests[0][1]) == 48
    assert requests[1:] == [("rconport", "27020"), ("rconenabled", "true")]
