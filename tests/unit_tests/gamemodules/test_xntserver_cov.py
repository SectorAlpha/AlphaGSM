"""Full coverage tests for xntserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.xntserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.xntserver as mod
    from server import ServerError

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=26000, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 26000

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 26000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["userdir"] = "test"
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["26001", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_configure_resolves_download(tmp_path):
    server = DummyServer()
    with patch.object(mod, 'resolve_download', return_value=('0.8.6', 'https://example.com/xonotic.zip')):
        mod.configure(server, ask=False, port=26000, dir=str(tmp_path))
    assert server.data['url'] == 'https://example.com/xonotic.zip'
    assert server.data['version'] == '0.8.6'

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "xonotic-linux64-dedicated"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    server.data["userdir"] = "user"
    server.data["hostname"] = "Test Server"
    server.data["gametype"] = "dm"
    mod.install(server)
    assert (tmp_path / "data" / "server.cfg").read_text(encoding="utf-8").startswith('hostname "Test Server"')
    assert (tmp_path / "user" / "data" / "server.cfg").exists()

def test_install_resolves_download(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "xonotic-linux64-dedicated"
    server.data["download_name"] = "test.zip"
    server.data["userdir"] = "user"
    server.data["hostname"] = "Test Server"
    server.data["gametype"] = "dm"
    with patch.object(mod, 'resolve_download', return_value=('0.8.6', 'https://example.com/xonotic.zip')):
        mod.install(server)
    assert server.data['url'] == 'https://example.com/xonotic.zip'
    assert (tmp_path / "data" / "server.cfg").exists()

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    launcher = tmp_path / "server" / "server_linux.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["userdir"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0] == "./server/server_linux.sh"
    assert "+port" in cmd
    assert cwd == server.data["dir"]


def test_get_start_command_nested_archive_root(tmp_path):
    server = DummyServer()
    content_root = tmp_path / "Xonotic"
    content_root.mkdir()
    launcher = content_root / "server" / "server_linux.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["userdir"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0] == "./server/server_linux.sh"
    assert cwd == str(content_root)


def test_get_start_command_prefers_upstream_wrapper_from_nested_archive_root(tmp_path):
    server = DummyServer()
    content_root = tmp_path / "Xonotic"
    content_root.mkdir()
    wrapper = content_root / "server" / "server_linux.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("")
    native_binary = content_root / "xonotic-linux64-dedicated"
    native_binary.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["userdir"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./server/server_linux.sh"
    assert cwd == str(content_root)


def test_get_container_spec_uses_nested_archive_workdir(tmp_path):
    server = DummyServer()
    content_root = tmp_path / "Xonotic"
    content_root.mkdir()
    launcher = content_root / "server" / "server_linux.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["userdir"] = "test"

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server/Xonotic"


def test_query_hooks_use_runtime_resolved_host(monkeypatch):
    server = DummyServer()
    server.data["port"] = 26000
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        lambda server_obj: "172.18.0.12",
    )

    expected = ("172.18.0.12", 26000, "quake")
    assert mod.get_query_address(server) == expected
    assert mod.get_info_address(server) == expected

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["gametype"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["userdir"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_prestart_refreshes_server_cfg(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["hostname"] = "AlphaGSM Test"
    server.data["gametype"] = "dm"
    server.data["userdir"] = "server"

    mod.prestart(server)

    assert (tmp_path / "data" / "server.cfg").exists()
    assert (tmp_path / "server" / "data" / "server.cfg").exists()


def test_prestart_refreshes_nested_archive_server_cfg(tmp_path):
    server = DummyServer()
    content_root = tmp_path / "Xonotic"
    content_root.mkdir()
    launcher = content_root / "server" / "server_linux.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["hostname"] = "AlphaGSM Test"
    server.data["gametype"] = "dm"
    server.data["userdir"] = "server"

    mod.prestart(server)

    assert (content_root / "data" / "server.cfg").exists()
    assert (content_root / "server" / "data" / "server.cfg").exists()

def test_do_stop():
    server = DummyServer()
    with patch.object(mod.runtime_module, "send_to_server") as mocked_send:
        mod.do_stop(server, 0)
    mocked_send.assert_called_with(server, "\nquit\n")

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

def test_checkvalue_url():
    server = DummyServer()
    result = mod.checkvalue(server, ("url",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_download_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("download_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_userdir():
    server = DummyServer()
    result = mod.checkvalue(server, ("userdir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_gametype():
    server = DummyServer()
    result = mod.checkvalue(server, ("gametype",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_version():
    server = DummyServer()
    result = mod.checkvalue(server, ("version",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
