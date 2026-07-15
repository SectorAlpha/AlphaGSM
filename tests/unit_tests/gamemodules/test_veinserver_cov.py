"""Full coverage tests for veinserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.veinserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.veinserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "VeinServer.sh"
    server.data["Steam_AppID"] = 2131400
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2131400
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2131400
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2131400
    server.data["Steam_anonymous_login_possible"] = True
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
    server.data["exe_name"] = "VeinServer.sh"
    (tmp_path / "VeinServer.sh").write_text("")
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./VeinServer.sh",
        "-Port=27015",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_prefers_resolved_nested_launcher(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "VeinServer.sh"
    nested_dir = tmp_path / "serverfiles"
    nested_dir.mkdir()
    nested_exe = nested_dir / "VeinServer.sh"
    nested_exe.write_text("", encoding="utf-8")
    (tmp_path / "VeinServer.sh").symlink_to(nested_exe)
    server.data["port"] = 27015

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./VeinServer.sh",
        "-Port=27015",
    ]
    assert cwd == str(nested_dir)


def test_setting_schema_exposes_vein_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_runtime_requirements_without_dir_keep_default_server_mount_behavior():
    server = DummyServer()
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    requirements = mod.get_runtime_requirements(server)

    assert requirements["family"] == "steamcmd-linux"
    assert "mounts" not in requirements


def test_get_container_spec_runs_as_non_root(tmp_path):
    server = DummyServer()
    (tmp_path / "VeinServer.sh").write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "VeinServer.sh",
            "port": 27015,
            "queryport": 27016,
        }
    )

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True
    assert any(
        mount["target"] == "/srv/server" and mount["mode"] == "rw"
        for mount in spec["mounts"]
    )
    assert any(
        mount["target"] == mod.CONTAINER_STEAMCMD_DIR and mount["mode"] == "ro"
        for mount in spec["mounts"]
    )
    shell_command = " ".join(spec["command"])
    assert 'useradd -M -u 1000 -o alphagsm;' in shell_command
    assert 'mkdir -p /home/alphagsm/.steam/sdk64;' in shell_command
    assert 'chmod -R a+rwX /srv/server /home/alphagsm;' in shell_command
    assert (
        'ln -sfn /opt/alphagsm-steamcmd/linux64/steamclient.so '
        '/home/alphagsm/.steam/sdk64/steamclient.so;'
    ) in shell_command
    assert 'export HOME=/home/alphagsm USER=alphagsm LOGNAME=alphagsm;' in shell_command
    assert (
        "exec runuser -u alphagsm -- sh -lc "
        "'cd /srv/server && ./VeinServer.sh -Port=27015 -QueryPort=27016'"
    ) in shell_command


def test_get_container_spec_rewrites_external_launcher_cwd(tmp_path):
    server = DummyServer()
    external_dir = tmp_path.parent / f"{tmp_path.name}-external-cache" / "vein"
    external_dir.mkdir(parents=True)
    external_launcher = external_dir / "VeinServer.sh"
    external_launcher.write_text("", encoding="utf-8")
    (tmp_path / "VeinServer.sh").symlink_to(external_launcher)
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "VeinServer.sh",
            "port": 27015,
            "queryport": 27016,
        }
    )

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == str(external_dir)
    assert any(
        mount["source"] == str(external_dir)
        and mount["target"] == str(external_dir)
        and mount["mode"] == "ro"
        for mount in spec["mounts"]
    )
    shell_command = " ".join(spec["command"])
    assert (
        "exec runuser -u alphagsm -- sh -lc "
        f"'cd {external_dir} && ./VeinServer.sh -Port=27015 -QueryPort=27016'"
    ) in shell_command
    assert "'cd /srv/server && ./VeinServer.sh -Port=27015 -QueryPort=27016'" not in shell_command


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
