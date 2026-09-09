"""Full coverage tests for lifeisfeudalserver."""

import os
import sys
from pathlib import Path
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
    assert '$cm_config::DB::Connect::server = "127.0.0.1:3306";' in written
    assert '$cm_config::DB::Connect::password = "secret";' in written


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


def test_launch_selects_native_world_one(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name="ddctd_cm_yo_server.exe")
    (tmp_path / server.data["exe_name"]).touch()
    assert mod.get_start_command(server)[0] == [server.data["exe_name"], "-worldID", "1"]


def test_world_port_sync_preserves_upstream_gameplay_settings(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=31000)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/default_world_config.xml").write_text(
        '<config><ID>1</ID><port>28000</port><skillcap>700</skillcap></config>'
    )
    mod.sync_server_config(server)
    world = tmp_path / "config/world_1.xml"
    assert '<port>31000</port>' in world.read_text()
    world.write_text(world.read_text().replace('700', '800'))
    server.data["port"] = 32000
    mod.sync_server_config(server)
    assert '<port>32000</port>' in world.read_text()
    assert '<skillcap>800</skillcap>' in world.read_text()
    assert mod.get_info_address(server) == ("127.0.0.1", 32002, "a2s")
    assert "port" in mod.config_sync_keys


def test_managed_database_uses_sidecar_address_for_bridge_game(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker", db_host="127.0.0.1",
                       db_port=4406, db_password="secret")
    monkeypatch.setattr(mod.runtime_module, "resolve_runtime_metadata",
                        lambda server: {"runtime": "docker", "network_mode": "bridge"})
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: True)
    docker = MagicMock(return_value=MagicMock(returncode=0, stdout='172.17.0.4\n', stderr=''))
    monkeypatch.setattr(mod, "_run_docker", docker)
    mod.sync_server_config(server)
    text = (tmp_path / "config_local.cs").read_text()
    assert '$cm_config::DB::Connect::server = "172.17.0.4:3306";' in text
    assert server.data["db_host"] == "127.0.0.1"
    assert server.data["db_port"] == 4406
    probe = MagicMock()
    monkeypatch.setattr(mod.socket, "create_connection", probe)
    mod._assert_database_endpoint_available(server)
    probe.assert_called_once_with(("127.0.0.1", 4406), timeout=1.0)


def test_managed_database_waits_when_existing_container_is_still_bootstrapping(monkeypatch):
    server = DummyServer()
    server.data.update(db_mode="docker", db_password="secret")
    monkeypatch.setattr(mod, "_docker_available", lambda: True)
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: True)
    ready = MagicMock(side_effect=[(False, 'initializing'), (True, '')])
    monkeypatch.setattr(mod, "_managed_database_ready", ready)
    grants = MagicMock()
    monkeypatch.setattr(mod, "_ensure_managed_root_grants", grants)
    monkeypatch.setattr(mod.time, "sleep", lambda delay: None)
    mod._ensure_managed_database(server)
    assert ready.call_count == 2
    grants.assert_called_once()


@pytest.mark.parametrize("backend,network", [("process", "bridge"), ("docker", "host")])
def test_database_host_endpoint_is_preserved_when_game_shares_host_network(monkeypatch, backend, network):
    server = DummyServer()
    server.data.update(db_mode="docker", db_host="127.0.0.1", db_port=4406)
    monkeypatch.setattr(mod.runtime_module, "resolve_runtime_metadata",
                        lambda server: {"runtime": backend, "network_mode": network})
    docker = MagicMock(side_effect=AssertionError("unexpected Docker inspection"))
    monkeypatch.setattr(mod, "_run_docker", docker)
    assert mod._database_address(server) == "127.0.0.1:4406"


@pytest.mark.parametrize("address", ["", "127.0.0.1", "0.0.0.0", "<no value>"])
def test_missing_sidecar_bridge_address_fails_instead_of_writing_loopback(monkeypatch, address):
    server = DummyServer()
    server.data.update(db_mode="docker")
    monkeypatch.setattr(mod.runtime_module, "resolve_runtime_metadata",
                        lambda server: {"runtime": "docker", "network_mode": "bridge"})
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: True)
    monkeypatch.setattr(mod, "_run_docker", MagicMock(
        return_value=MagicMock(returncode=0, stdout=address, stderr='')))
    with pytest.raises(ServerError, match="bridge address"):
        mod._database_address(server)


def test_prestart_refreshes_database_address_only_after_sidecar_is_ready(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker")
    calls = []
    monkeypatch.setattr(mod, "_ensure_managed_database", lambda server: calls.append("ready"))
    monkeypatch.setattr(mod, "sync_server_config", lambda server: calls.append("config"))
    monkeypatch.setattr(mod, "_assert_database_endpoint_available", lambda server: calls.append("probe"))
    mod.prestart(server)
    assert calls == ["ready", "config", "probe"]


def test_world_config_without_native_port_fails_without_overwriting_it(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=31000)
    (tmp_path / "config").mkdir()
    world = tmp_path / "config/world_1.xml"
    world.write_text('<config><skillcap>800</skillcap></config>')
    with pytest.raises(ServerError, match="one <port>"):
        mod.sync_server_config(server)
    assert world.read_text() == '<config><skillcap>800</skillcap></config>'


def test_lifeisfeudal_runtime_builders_receive_complete_native_port_group(monkeypatch):
    server = DummyServer()
    requirements = MagicMock(return_value={})
    spec = MagicMock(return_value={})
    monkeypatch.setattr(mod.proton, "get_runtime_requirements", requirements)
    monkeypatch.setattr(mod.proton, "get_container_spec", spec)
    mod.get_runtime_requirements(server)
    mod.get_container_spec(server)
    expected = {(offset, protocol) for offset in (0, 1, 2) for protocol in ("tcp", "udp")}
    for call in (requirements.call_args, spec.call_args):
        assert {(entry["offset"], entry["protocol"])
                for entry in call.kwargs["port_definitions"]} == expected
        assert all(entry["key"] == "port" for entry in call.kwargs["port_definitions"])


def test_managed_docker_game_does_not_probe_manager_container_loopback(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker")
    monkeypatch.setattr(mod, "_ensure_managed_database", lambda server: None)
    monkeypatch.setattr(mod, "sync_server_config", lambda server: None)
    monkeypatch.setattr(mod.runtime_module, "resolve_runtime_metadata",
                        lambda server: {"runtime": "docker", "network_mode": "bridge"})
    monkeypatch.setattr(mod.socket, "create_connection", MagicMock(
        side_effect=AssertionError("manager loopback is not the Docker host")))
    mod.prestart(server)


def test_legacy_managed_fallback_gains_native_database_keys(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_host="db.internal", db_password="updated")
    config = tmp_path / "config_local.cs"
    config.write_text('// Managed by AlphaGSM when no upstream template is present.\n'
                      '$DatabaseAddress = "127.0.0.1:3306";\n'
                      '$DatabasePassword = "old";\n$customSetting = "preserved";\n')
    mod.sync_server_config(server)
    written = config.read_text()
    assert '$cm_config::DB::Connect::server = "db.internal:3306";' in written
    assert '$cm_config::DB::Connect::password = "updated";' in written
    assert '$customSetting = "preserved";' in written


def test_sidecar_leaves_schema_creation_to_native_world_bootstrap(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker", db_password="secret", db_user="lif_user")
    monkeypatch.setattr(mod, "_docker_available", lambda: True)
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: False)
    monkeypatch.setattr(mod, "_docker_container_exists", lambda name: False)
    docker = MagicMock(return_value=MagicMock(returncode=0, stdout='', stderr=''))
    monkeypatch.setattr(mod, "_run_docker", docker)
    monkeypatch.setattr(mod, "_managed_database_ready", lambda *_a: (True, ''))
    mod._ensure_managed_database(server)
    command = docker.call_args_list[0].args
    assert command[0] == "run"
    assert not any(arg.startswith("MYSQL_DATABASE=") for arg in command)
    sql = next(call.args[-1] for call in docker.call_args_list if call.args[0] == "exec")
    assert "CREATE DATABASE" not in sql
    assert "CREATE USER IF NOT EXISTS 'lif_user'@'%'" in sql
    assert "GRANT ALL PRIVILEGES ON `lif_1`.* TO 'lif_user'@'%'" in sql


def test_database_grants_quote_operator_credentials(monkeypatch):
    docker = MagicMock(return_value=MagicMock(returncode=0, stdout='', stderr=''))
    monkeypatch.setattr(mod, "_run_docker", docker)
    mod._ensure_managed_root_grants("fixture", "p'ass", db_user="u'ser", db_name="lif`one")
    sql = docker.call_args.args[-1]
    assert "IDENTIFIED BY 'p''ass'" in sql
    assert "'u''ser'@'%'" in sql
    assert "ON `lif``one`.*" in sql


def test_sidecar_translates_nested_manager_mounts_without_changing_data(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker", db_password="secret")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/my.ini").write_text('[mysqld]\nmax_allowed_packet=10M\n')
    data = tmp_path / ".alphagsm/mariadb-data"
    data.mkdir(parents=True)
    existing = data / "existing.ibd"
    existing.write_bytes(b"operator database contents")
    monkeypatch.setattr(mod, "_docker_available", lambda: True)
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: False)
    monkeypatch.setattr(mod, "_docker_container_exists", lambda name: False)
    monkeypatch.setattr(mod, "_managed_database_ready", lambda *_a: (True, ''))
    monkeypatch.setattr(mod, "_ensure_managed_root_grants", lambda *_a, **_kw: None)
    monkeypatch.setattr(mod.runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(mod.runtime_module, "_current_container_bind_mounts", lambda: [
        {"source": "/daemon/work", "destination": str(tmp_path)}
    ])
    docker = MagicMock(return_value=MagicMock(returncode=0, stdout='', stderr=''))
    monkeypatch.setattr(mod, "_run_docker", docker)

    mod._ensure_managed_database(server)

    command = docker.call_args.args
    assert "/daemon/work/.alphagsm/mariadb-data:/var/lib/mysql:rw" in command
    assert "/daemon/work/.alphagsm/lif-mariadb.cnf:/etc/mysql/conf.d/lif-mariadb.cnf:ro" in command
    assert not any(str(tmp_path) in arg for arg in command)
    assert existing.read_bytes() == b"operator database contents"
    assert (tmp_path / ".alphagsm/lif-mariadb.cnf").read_text() == '[mysqld]\nmax_allowed_packet=10M\n'


def test_sidecar_fails_before_docker_run_when_manager_path_is_unmapped(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), db_mode="docker", db_password="secret")
    monkeypatch.setattr(mod, "_docker_available", lambda: True)
    monkeypatch.setattr(mod, "_docker_container_running", lambda name: False)
    monkeypatch.setattr(mod, "_docker_container_exists", lambda name: False)
    monkeypatch.setattr(mod.runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(mod.runtime_module, "_current_container_bind_mounts", lambda: [])
    docker = MagicMock(side_effect=AssertionError("unmapped sidecar must not launch"))
    monkeypatch.setattr(mod, "_run_docker", docker)

    with pytest.raises(mod.runtime_module.RuntimeError, match="host-visible bind-mount mapping"):
        mod._ensure_managed_database(server)

    docker.assert_not_called()


def test_native_plaintext_credential_sink_has_codeql_suppression():
    source = Path(mod.__file__).with_name("main.py").read_text(encoding="utf-8")
    sink = next(
        line for line in reversed(source.splitlines()) if "handle.write(text)" in line
    )

    assert "lgtm[py/clear-text-storage-sensitive-data]" in sink
