"""Full coverage tests for mtaserver."""

from pathlib import Path
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.mtaserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.mtaserver as mod
    import gamemodules.mtaserver.main as mod_main
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=22003, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 22003
    assert server.data["httpport"] == 22005
    assert server.data["httpport_explicit"] is False
    assert server.data['mods']['desired']['url'] == []

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 22003
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["22004", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_configure_resolves_download(tmp_path):
    server = DummyServer()
    with patch.object(mod_main, 'resolve_download', return_value=('1.6', 'https://example.com/mta.tar.gz')):
        mod.configure(server, ask=False, port=22003, dir=str(tmp_path))
    assert server.data['url'] == 'https://example.com/mta.tar.gz'
    assert server.data['version'] == '1.6'

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mta-server64"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    server.data["port"] = 22003
    server.data["httpport"] = 22005
    with patch.object(mod_main, "_download_mta_baseconfig") as mock_download, patch.object(
        mod_main, "extract_tarball_safe"
    ) as mock_extract, patch.object(mod_main, "sync_tree") as mock_sync:
        mod.install(server)
    mod_main.install_archive.assert_called_once()
    mock_download.assert_called_once()
    mock_extract.assert_called_once()
    mock_sync.assert_called_once()

def test_install_resolves_download(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mta-server64"
    server.data["download_name"] = "test.tar.gz"
    with patch.object(mod_main, 'resolve_download', return_value=('1.6', 'https://example.com/mta.tar.gz')), patch.object(
        mod_main, "_download_mta_baseconfig"
    ), patch.object(mod_main, "extract_tarball_safe"), patch.object(mod_main, "sync_tree"):
        mod.install(server)
    assert server.data['url'] == 'https://example.com/mta.tar.gz'


def test_sync_server_config_updates_managed_ports(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 22110
    server.data["httpport"] = 22112
    config_path = tmp_path / "mods" / "deathmatch" / "mtaserver.conf"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "<serverport>22003</serverport>\n"
        "<httpserver>0</httpserver>\n"
        "<httpport>22005</httpport>\n"
        "<ase>1</ase>\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    text = config_path.read_text(encoding="utf-8")
    assert "<serverport>22110</serverport>" in text
    assert "<httpserver>1</httpserver>" in text
    assert "<httpport>22112</httpport>" in text
    assert "<ase>0</ase>" in text


def test_sync_server_config_is_noop_without_existing_file(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 22003
    server.data["httpport"] = 22005

    mod.sync_server_config(server)

    assert not (tmp_path / "mods" / "deathmatch" / "mtaserver.conf").exists()


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mta-server64"
    (tmp_path / "mta-server64").write_text("")
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_prestart_calls_sync_server_config(monkeypatch):
    server = DummyServer()
    calls = []
    monkeypatch.setattr(mod, "sync_server_config", lambda current: calls.append(current))

    mod.prestart(server)

    assert calls == [server]

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


def test_checkvalue_httpport():
    server = DummyServer()
    result = mod.checkvalue(server, ("httpport",), "12347")
    assert result == 12347

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

def test_checkvalue_version():
    server = DummyServer()
    result = mod.checkvalue(server, ("version",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")


def test_postset_updates_derived_httpport_when_not_explicit(monkeypatch):
    server = DummyServer()
    server.data["port"] = 22120
    server.data["httpport"] = 22005
    server.data["httpport_explicit"] = False
    calls = []
    monkeypatch.setattr(mod, "sync_server_config", lambda current: calls.append(current))

    mod.postset(server, ("port",))

    assert server.data["httpport"] == 22122
    assert calls == [server]


def test_postset_marks_httpport_explicit_and_syncs(monkeypatch):
    server = DummyServer()
    server.data["httpport"] = 22125
    calls = []
    monkeypatch.setattr(mod, "sync_server_config", lambda current: calls.append(current))

    mod.postset(server, ("httpport",))

    assert server.data["httpport_explicit"] is True
    assert calls == [server]


def test_get_query_and_info_address_use_http_listener():
    server = DummyServer()
    server.data["port"] = 22003
    server.data["httpport"] = 22005

    assert mod.get_query_address(server) == ("127.0.0.1", 22005, "tcp")
    assert mod.get_info_address(server) == ("127.0.0.1", 22005, "tcp")


def test_runtime_requirements_and_container_spec_publish_game_and_http_ports(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mta-server64",
            "port": 22003,
            "httpport": 22005,
        }
    )
    exe_path = Path(tmp_path) / "mta-server64"
    exe_path.write_text("", encoding="utf-8")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 22003, "container": 22003, "protocol": "udp"},
        {"host": 22005, "container": 22005, "protocol": "tcp"},
    ]
    assert spec["ports"] == requirements["ports"]
    assert spec["working_dir"] == mod.runtime_module.DEFAULT_CONTAINER_WORKDIR
