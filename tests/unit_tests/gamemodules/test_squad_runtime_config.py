"""Squad native RCON configuration and listener ownership."""
from importlib import import_module

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def configured_server(tmp_path):
    """Create a disposable configured server without SteamCMD."""
    module = import_module("gamemodules.squadserver")
    server = DummyServer("squadnative")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    return module, server


def test_native_rcon_sync_preserves_operator_settings_and_exposes_real_protocol(tmp_path):
    module, server = configured_server(tmp_path)
    config = tmp_path / "SquadGame/ServerConfig/Rcon.cfg"
    config.parent.mkdir(parents=True)
    config.write_text("// operator comment\nMaxConnections=7\nPort=21114\nPassword=\n")
    server.data["rconport"] = "28301"
    server.data["adminpassword"] = "local-test-password"
    module.sync_server_config(server)
    text = config.read_text()
    assert "MaxConnections=7" in text and "// operator comment" in text
    assert "Port=28301" in text and "Password=local-test-password" in text
    assert "Port=21114" not in text
    assert text.count("Password=") == 1
    assert config.stat().st_mode & 0o777 == 0o600
    assert module.get_info_address(server) == ("127.0.0.1", 28301, "squad_rcon")
    assert module.get_query_address(server) == module.get_info_address(server)
    assert {"rconport", "adminpassword"} <= set(module.config_sync_keys)


def test_generated_rcon_password_is_stable_and_all_native_ports_are_claimed(tmp_path):
    module, server = configured_server(tmp_path)
    password = server.data["adminpassword"]
    assert isinstance(password, str) and len(password) >= 24
    assert module.setting_schema["adminpassword"].secret
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    assert server.data["adminpassword"] == password
    definitions = module.port_claim_definitions
    assert {"port", "queryport", "rconport", "beaconport"} <= {
        entry["key"] for entry in definitions}
    requirements = module.get_runtime_requirements(server)
    assert any(item["host"] == int(server.data["rconport"])
               and item["protocol"] == "tcp" for item in requirements["ports"])


def test_rcon_config_symlink_or_line_injection_never_writes(tmp_path):
    module, server = configured_server(tmp_path)
    with pytest.raises(ServerError):
        module.checkvalue(server, ["adminpassword"], "unsafe\nRCONIP=evil")
    outside = tmp_path / "operator.cfg"
    outside.write_text("operator")
    config = tmp_path / "SquadGame/ServerConfig/Rcon.cfg"
    config.parent.mkdir(parents=True)
    config.symlink_to(outside)
    with pytest.raises(ServerError):
        module.sync_server_config(server)
    assert outside.read_text() == "operator"


def test_squad44_beacon_listener_tracks_configured_port_and_docker(tmp_path):
    """Two managed Squad 44 servers must not silently share native beacon15000."""
    module = import_module("gamemodules.squad44server")
    server = DummyServer("squad44native")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    (tmp_path / "PostScriptumServer.sh").write_text("#!/bin/sh\n")
    server.data["beaconport"] = "28311"
    command, _directory = module.get_start_command(server)
    assert "beaconport=28311" in command
    assert any(entry["key"] == "beaconport" and entry["protocol"] == "udp"
               for entry in module.port_claim_definitions)
    assert any(entry["host"] == 28311 for entry in module.get_runtime_requirements(server)["ports"])


def test_update_restores_native_rcon_config_before_restart(tmp_path, monkeypatch):
    """An upstream depot refresh must not leave the query disabled after restart."""
    module, server = configured_server(tmp_path)
    config = tmp_path / "SquadGame/ServerConfig/Rcon.cfg"
    config.parent.mkdir(parents=True)
    (tmp_path / "SquadGameServer.sh").write_text("#!/bin/sh\n")
    config.write_text("Password=old\n")
    def download(*_args, **_kwargs):
        config.write_text("// upstream template\nPassword=\n")
    monkeypatch.setattr(module.steamcmd, "download", download)
    def start():
        assert f"Password={server.data['adminpassword']}" in config.read_text()
    monkeypatch.setattr(server, "start", start)
    module.update(server, restart=True)
