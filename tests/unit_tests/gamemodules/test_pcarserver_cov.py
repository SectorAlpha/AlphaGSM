"""Full coverage tests for pcarserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.pcarserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.pcarserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["configfile"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServerCmd"
    server.data["Steam_AppID"] = 332670
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 27015
    mod.install(server)
    assert (tmp_path / "server.cfg").exists()
    assert "hostPort : 27015" in (tmp_path / "server.cfg").read_text()
    assert "queryPort : 27016" in (tmp_path / "server.cfg").read_text()


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 332670
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 27015
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 332670
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 27015
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 332670
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 27015
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServerCmd"
    (tmp_path / "DedicatedServerCmd").write_text("")
    server.data["configfile"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["./DedicatedServerCmd"]
    assert cwd == server.data["dir"]


def test_get_start_command_prefers_resolved_nested_launcher(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServerCmd"
    nested_dir = tmp_path / "serverfiles"
    nested_dir.mkdir()
    nested_exe = nested_dir / "DedicatedServerCmd"
    nested_exe.write_text("", encoding="utf-8")
    (tmp_path / "DedicatedServerCmd").symlink_to(nested_exe)
    server.data["configfile"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd == ["./DedicatedServerCmd"]
    assert cwd == str(nested_dir)


def test_query_and_info_address_use_game_port(monkeypatch):
    server = DummyServer("pcar")
    server.data["port"] = "27015"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.10", 27016, "a2s")


def test_query_and_info_address_use_explicit_query_port(monkeypatch):
    server = DummyServer("pcar")
    server.data["port"] = "27015"
    server.data["queryport"] = "28000"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 28000, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.10", 28000, "a2s")


def test_sync_server_config_writes_canonical_server_cfg(tmp_path):
    server = DummyServer("pcar")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 27015
    server.data["configfile"] = "custom.cfg"

    mod.sync_server_config(server)

    assert 'name : "AlphaGSM pcar"' in (tmp_path / "custom.cfg").read_text()
    assert "hostPort : 27015" in (tmp_path / "server.cfg").read_text()
    assert "queryPort : 27016" in (tmp_path / "server.cfg").read_text()


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["configfile"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)


def test_message():
    server = DummyServer()
    mod.message(server, "hello")


def test_backup():
    server = DummyServer()
    server.data["dir"] = "/tmp/test/"
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.backup(server)


def test_checkvalue_empty_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ())


def test_checkvalue_unsupported_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")


def test_checkvalue_no_value():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",))


def test_checkvalue_port():
    server = DummyServer()
    result = mod.checkvalue(server, ("port",), "12345")
    assert result == 12345


def test_checkvalue_configfile():
    server = DummyServer()
    result = mod.checkvalue(server, ("configfile",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")


@pytest.mark.parametrize("query_port", [None, 31000])
def test_runtime_publishes_native_query_port(tmp_path, query_port):
    server = DummyServer("pcar")
    server.data.update({"dir": str(tmp_path), "port": 29589, "exe_name": "DedicatedServerCmd"})
    (tmp_path / "DedicatedServerCmd").touch()
    if query_port is not None:
        server.data["queryport"] = query_port
    expected = query_port or 29590

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    for runtime in (requirements, spec):
        assert {"host": expected, "container": expected, "protocol": "udp"} in runtime["ports"]
    mod.sync_server_config(server)
    assert f"queryPort : {expected}" in (tmp_path / "server.cfg").read_text()
    assert "queryport" in mod.config_sync_keys
    assert mod.checkvalue(server, ("queryport",), "31000") == 31000


def test_runtime_requirements_before_setup():
    assert mod.get_runtime_requirements(DummyServer())["ports"] == [
        {"host": 8766, "container": 8766, "protocol": "udp"},
    ]


@pytest.mark.parametrize("query_port", [None, 31000])
def test_process_claims_the_native_query_port(monkeypatch, query_port):
    from server.port_manager import collect_claim_set
    server = DummyServer("pcar")
    server.module = mod
    server.data.update({"port": 29589, "runtime": {"backend": "process"}})
    if query_port is not None:
        server.data["queryport"] = query_port
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "127.0.0.1")

    claims = collect_claim_set(server)

    assert (query_port or 29590) in {endpoint.port for endpoint in claims.endpoints}


@pytest.mark.parametrize("steam_port", [None, 28766])
def test_steam_port_config_runtime_and_process_claims(tmp_path, monkeypatch, steam_port):
    from server.port_manager import collect_claim_set
    server = DummyServer("pcar")
    server.module = mod
    if steam_port is not None:
        server.data["steamport"] = steam_port
    mod.configure(server, ask=False, port=29589, dir=str(tmp_path))
    (tmp_path / "DedicatedServerCmd").touch()
    expected = steam_port or 8766

    assert server.data["steamport"] == expected
    mod.sync_server_config(server)
    assert f"steamPort : {expected}" in (tmp_path / "server.cfg").read_text()
    for runtime in (mod.get_runtime_requirements(server), mod.get_container_spec(server)):
        assert {"host": expected, "container": expected, "protocol": "udp"} in runtime["ports"]
        assert {"host": 29590, "container": 29590, "protocol": "udp"} in runtime["ports"]
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "127.0.0.1")
    assert expected in {endpoint.port for endpoint in collect_claim_set(server).endpoints}
    assert "steamport" in mod.config_sync_keys
    assert mod.checkvalue(server, ("steamport",), "28766") == 28766


def test_legacy_steam_port_is_claimed_and_published_without_datastore_mutation(tmp_path):
    from server.port_manager import collect_claim_set
    server = DummyServer("pcar")
    server.module = mod
    server.data.update(dir=str(tmp_path), port=29589, exe_name="DedicatedServerCmd")
    (tmp_path / "DedicatedServerCmd").touch()
    original = dict(server.data)
    assert 8766 in {endpoint.port for endpoint in collect_claim_set(server).endpoints}
    for metadata in (mod.get_runtime_requirements(server), mod.get_container_spec(server)):
        assert {"host": 8766, "container": 8766, "protocol": "udp"} in metadata["ports"]
    assert dict(server.data) == original
