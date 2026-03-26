"""Unit tests for the identityserver game module (archive-download pattern)."""

from types import SimpleNamespace

import importlib
import os

import pytest


def _make_server(name="alpha"):
    data = {}

    class SaveDict(dict):
        def save(self):
            pass

    return SimpleNamespace(name=name, data=SaveDict(data))


def test_identityserver_configure_defaults(tmp_path):
    module = importlib.import_module("gamemodules.identityserver")
    server = _make_server()

    module.configure(
        server,
        False,
        port=7777,
        dir=str(tmp_path / "identity"),
        url="https://example.com/identity-server.zip",
        download_name="identity-server.zip",
    )

    assert server.data["port"] == 7777
    assert server.data["dir"] == str(tmp_path / "identity") + "/"
    assert server.data["url"] == "https://example.com/identity-server.zip"
    assert server.data["download_name"] == "identity-server.zip"
    assert server.data["exe_name"] == "IdentityServer.x86_64"
    assert server.data["backupfiles"] == ["Config", "Saves", "Logs"]


def test_identityserver_get_start_command(tmp_path):
    module = importlib.import_module("gamemodules.identityserver")
    server = _make_server()

    module.configure(
        server,
        False,
        port=8888,
        dir=str(tmp_path),
        url="https://example.com/identity-server.zip",
    )

    exe = tmp_path / "IdentityServer.x86_64"
    exe.write_text("")

    cmd, cwd = module.get_start_command(server)

    assert cmd == ["./IdentityServer.x86_64", "-port", "8888"]
    assert cwd == server.data["dir"]


def test_identityserver_install_requires_url():
    module = importlib.import_module("gamemodules.identityserver")
    server = _make_server()
    server.data["url"] = ""
    server.data["dir"] = "/tmp/test/"
    server.data["download_name"] = "identity-server.zip"

    with pytest.raises(Exception):
        module.install(server)


def test_identityserver_checkvalue_port():
    module = importlib.import_module("gamemodules.identityserver")
    server = _make_server()
    server.data["backup"] = {}

    result = module.checkvalue(server, ("port",), "9999")
    assert result == 9999


def test_identityserver_checkvalue_invalid_key():
    module = importlib.import_module("gamemodules.identityserver")
    server = _make_server()
    server.data["backup"] = {}

    with pytest.raises(Exception):
        module.checkvalue(server, ("unknown_key",), "value")
