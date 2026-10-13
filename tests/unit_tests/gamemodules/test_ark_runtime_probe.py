"""Optional native ARK RCON supports actual engine-object verification."""
from importlib import import_module

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def prepared(tmp_path):
    """Configure a tiny native launch fixture."""
    module = import_module("gamemodules.ark")
    server = DummyServer("arknative")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    executable = tmp_path / server.data["exe_name"]
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    return module, server


def test_rcon_remains_disabled_until_explicitly_enabled_with_private_password(tmp_path):
    module, server = prepared(tmp_path)
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=" not in command[1]
    with pytest.raises(ServerError, match="password"):
        module.checkvalue(server, ["rconenabled"], "true")
    server.data["adminpassword"] = "generated-local-password"
    server.data["rconenabled"] = module.checkvalue(server, ["rconenabled"], "true")
    server.data["rconport"] = module.checkvalue(server, ["rconport"], "28312")
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=True?RCONPort=28312" in command[1]
    assert any(item["key"] == "rconport" and item["protocol"] == "tcp"
               for item in module.port_claim_definitions)
    assert any(item["host"] == 28312 and item["protocol"] == "tcp"
               for item in module.get_runtime_requirements(server)["ports"])


def test_false_rcon_value_and_bad_boolean_never_enable_listener(tmp_path):
    module, server = prepared(tmp_path)
    server.data["rconenabled"] = module.checkvalue(server, ["rconenabled"], "false")
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=" not in command[1]
    with pytest.raises(ServerError):
        module.checkvalue(server, ["rconenabled"], "maybe")
