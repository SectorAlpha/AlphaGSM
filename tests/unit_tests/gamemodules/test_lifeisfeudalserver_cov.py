"""Full coverage tests for lifeisfeudalserver."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.lifeisfeudalserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.lifeisfeudalserver as mod
    from server import ServerError

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28000, dir=str(tmp_path))
    assert server.data['port'] == 28000
    assert server.data["db_mode"] == "local"
    assert server.data["db_host"] == "127.0.0.1"
    assert server.data["db_port"] == 3306
    assert server.data["db_name"] == "lif_1"
    assert server.data["db_user"] == "root"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr(mod.getpass, "getpass", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 28000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    server.data["rconport"] = 27015
    server.data["db_mode"] = "local"
    server.data["db_host"] = "127.0.0.1"
    server.data["db_port"] = 3306
    server.data["db_name"] = "lif_1"
    server.data["db_user"] = "root"
    server.data["db_password"] = ""
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["28001", str(tmp_path / 'custom'), "docker", "127.0.0.1", "4406", "lif_custom", "lif_user"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    monkeypatch.setattr(mod.getpass, "getpass", lambda prompt: "secretpass")
    server = DummyServer()
    mod.configure(server, ask=True)
    assert server.data["db_mode"] == "docker"
    assert server.data["db_host"] == "127.0.0.1"
    assert server.data["db_port"] == 4406
    assert server.data["db_name"] == "lif_custom"
    assert server.data["db_user"] == "lif_user"
    assert server.data["db_password"] == "secretpass"


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ddctd_cm_yo_server.exe"
    server.data["Steam_AppID"] = 320850
    server.data["Steam_anonymous_login_possible"] = True
    server.data["db_mode"] = "local"
    server.data["db_host"] = "127.0.0.1"
    server.data["db_port"] = 3306
    server.data["db_name"] = "lif_1"
    server.data["db_user"] = "root"
    server.data["db_password"] = "secret"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "config_local.cs").write_text('DatabaseAddress = "127.0.0.1:3306"\nrootPassword = ""\n')
    mod.install(server)
    assert (tmp_path / "config_local.cs").is_file()


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 320850
    server.data["Steam_anonymous_login_possible"] = True
    server.data["db_mode"] = "local"
    server.data["db_host"] = "127.0.0.1"
    server.data["db_port"] = 3306
    server.data["db_name"] = "lif_1"
    server.data["db_user"] = "root"
    server.data["db_password"] = ""
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 320850
    server.data["Steam_anonymous_login_possible"] = True
    server.data["db_mode"] = "local"
    server.data["db_host"] = "127.0.0.1"
    server.data["db_port"] = 3306
    server.data["db_name"] = "lif_1"
    server.data["db_user"] = "root"
    server.data["db_password"] = ""
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 320850
    server.data["Steam_anonymous_login_possible"] = True
    server.data["db_mode"] = "local"
    server.data["db_host"] = "127.0.0.1"
    server.data["db_port"] = 3306
    server.data["db_name"] = "lif_1"
    server.data["db_user"] = "lif_1"
    server.data["db_password"] = ""
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ddctd_cm_yo_server.exe",
            "db_mode": "local",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "secret",
        }
    )
    (tmp_path / "ddctd_cm_yo_server.exe").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert not (tmp_path / "config_local.cs").exists()


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_prestart_requires_configured_mysql(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod.socket,
        "create_connection",
        MagicMock(side_effect=OSError("connection refused")),
    )
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ddctd_cm_yo_server.exe",
            "db_mode": "local",
            "db_host": "db.internal",
            "db_port": 4406,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "",
        }
    )
    with pytest.raises(ServerError, match="db.internal:4406"):
        mod.prestart(server)


def test_sync_server_config_copies_docs_template_and_rewrites_values(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "db_mode": "local",
            "db_host": "db.internal",
            "db_port": 4406,
            "db_name": "lif_custom",
            "db_user": "lif_user",
            "db_password": "secretpass",
        }
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "config_local.cs").write_text(
        '\n'.join(
            [
                '$cm_config::DB::Connect::server = "127.0.0.1:3306"',
                '$cm_config::DB::Connect::user = "root"',
                '$cm_config::DB::Connect::password = "rootPassword"',
            ]
        )
    )

    mod.sync_server_config(server)

    written = (tmp_path / "config_local.cs").read_text()
    assert '$cm_config::DB::Connect::server = "db.internal:4406"' in written
    assert '$cm_config::DB::Connect::user = "lif_user"' in written
    assert '$cm_config::DB::Connect::password = "secretpass"' in written


def test_sync_server_config_writes_managed_fallback_when_docs_template_missing(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "db_mode": "local",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "secret",
        }
    )

    mod.sync_server_config(server)

    written = (tmp_path / "config_local.cs").read_text()
    assert "Managed by AlphaGSM" in written
    assert '$DatabaseAddress = "127.0.0.1:3306";' in written
    assert '$DatabasePassword = "secret";' in written


def test_prestart_managed_docker_requires_password(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "db_mode": "docker",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "",
        }
    )

    with pytest.raises(ServerError, match="db_password"):
        mod.prestart(server)


def test_prestart_managed_docker_rejects_non_local_host(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "db_mode": "docker",
            "db_host": "db.internal",
            "db_port": 3306,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "secret",
        }
    )

    with pytest.raises(ServerError, match="db_host"):
        mod.prestart(server)


def test_prestart_managed_docker_starts_sidecar_and_waits(tmp_path, monkeypatch):
    fake_conn = MagicMock()
    monkeypatch.setattr(mod, "_docker_available", lambda: True)
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: False)
    monkeypatch.setattr(mod, "_docker_container_exists", lambda name: False)
    docker_calls = []

    def fake_run_docker(*args, **kwargs):
        docker_calls.append(args)
        return MagicMock(returncode=0, stdout="container-id\n", stderr="")

    monkeypatch.setattr(mod, "_run_docker", fake_run_docker)
    monkeypatch.setattr(mod.socket, "create_connection", lambda *args, **kwargs: fake_conn)
    server = DummyServer("lif docker")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "db_mode": "docker",
            "db_host": "127.0.0.1",
            "db_port": 4406,
            "db_name": "lif_1",
            "db_user": "lif_1",
            "db_password": "secret",
        }
    )

    mod.prestart(server)

    assert any(call[0] == "run" for call in docker_calls)
    assert (tmp_path / "config_local.cs").is_file()
    assert fake_conn.close.call_count >= 1


def test_do_stop(monkeypatch):
    server = DummyServer()
    send_mock = MagicMock()
    monkeypatch.setattr(mod.runtime_module, "send_to_server", send_mock)
    mod.do_stop(server, 0)
    send_mock.assert_called_once_with(server, "\003")


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_rconport():
    server = DummyServer()
    result = mod.checkvalue(server, ("rconport",), "12345")
    assert result == 12345


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_db_mode():
    server = DummyServer()
    result = mod.checkvalue(server, ("db_mode",), "managed-docker")
    assert result == "docker"


def test_checkvalue_db_port_alias():
    server = DummyServer()
    result = mod.checkvalue(server, ("dbport",), "4406")
    assert result == 4406


def test_checkvalue_db_password():
    server = DummyServer()
    result = mod.checkvalue(server, ("db_password",), "secret")
    assert result == "secret"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
