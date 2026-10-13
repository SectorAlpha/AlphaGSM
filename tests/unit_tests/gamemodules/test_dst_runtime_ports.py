"""DST port claims must match the native shard INI and Steam query endpoint."""

import configparser

import pytest

import gamemodules.dstserver as mod
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def test_native_ports_sync_preserves_operator_settings_and_token(tmp_path):
    server = DummyServer("dstports")
    mod.configure(server, False, port=18000, dir=str(tmp_path))
    server.data.update(queryport=18001, authport=18002)
    cluster = tmp_path / "DoNotStarveTogether" / server.name
    shard = cluster / "Master"
    shard.mkdir(parents=True)
    token = cluster / "cluster_token.txt"
    token.write_text("private-test-token")
    native = shard / "server.ini"
    native.write_text('[NETWORK]\nserver_port=10999\n[STEAM]\nmaster_server_port=27016\n'
                      'authentication_port=8766\n[SHARD]\nis_master=true\nname=Operator\n')
    mod.sync_server_config(server)
    config = configparser.ConfigParser(interpolation=None)
    config.read(native)
    assert config["NETWORK"]["server_port"] == "18000"
    assert config["STEAM"]["master_server_port"] == "18001"
    assert config["STEAM"]["authentication_port"] == "18002"
    assert config["SHARD"]["name"] == "Operator"
    assert token.read_text() == "private-test-token"
    assert mod.get_query_address(server) == ("127.0.0.1", 18001, "a2s")
    assert mod.get_info_address(server) == mod.get_query_address(server)
    assert set(mod.config_sync_keys) == {"port", "queryport", "authport"}
    ports = mod.get_runtime_requirements(server)["ports"]
    assert {(entry["host"], entry["protocol"]) for entry in ports} >= {
        (18000, "udp"), (18001, "udp"), (18002, "udp")
    }


def test_missing_supplied_cluster_is_not_fabricated_by_sync(tmp_path):
    server = DummyServer("dstports")
    mod.configure(server, False, port=18000, dir=str(tmp_path))
    mod.sync_server_config(server)
    assert not (tmp_path / "DoNotStarveTogether").exists()


def test_native_port_sync_rejects_symlinked_cluster(tmp_path):
    server = DummyServer("dstports")
    mod.configure(server, False, port=18000, dir=str(tmp_path / "install"))
    outside = tmp_path / "outside"
    outside.mkdir()
    config_root = tmp_path / "install" / "DoNotStarveTogether"
    config_root.mkdir(parents=True)
    (config_root / server.name).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError):
        mod.sync_server_config(server)


@pytest.mark.parametrize("key", ["queryport", "authport"])
def test_native_port_settings_validate_and_convert(key):
    server = DummyServer()
    assert mod.checkvalue(server, (key,), "18001") == 18001
    for value in ("0", "65536", "-1", "bad"):
        with pytest.raises(ServerError):
            mod.checkvalue(server, (key,), value)


def test_provider_requirement_is_klei_token_and_registry_auth(tmp_path):
    from pathlib import Path
    server = DummyServer("dstauth")
    mod.configure(server, False, port=18000, dir=str(tmp_path))
    requirements = mod.get_provider_requirements(server)
    assert requirements[0]["provider"] == "klei"
    assert requirements[0]["support_category"] == "provider-token"
    assert requirements[0]["required_for"] == ("start",)
    assert requirements[0]["path"].endswith("dstauth/cluster_token.txt")
    assert "dstserver\tprovider-token\t" in Path("enabled_auth_servers.conf").read_text()
    assert not any(line.startswith("dstserver\t")
                   for line in Path("enabled_byo_servers.conf").read_text().splitlines())


@pytest.mark.parametrize("token_content", [None, ""])
def test_missing_or_empty_token_uses_shared_auth_guidance(tmp_path, token_content):
    server = DummyServer("dstauth")
    mod.configure(server, False, port=18000, dir=str(tmp_path))
    cluster = tmp_path / "DoNotStarveTogether" / server.name
    (cluster / "Master").mkdir(parents=True)
    (cluster / "cluster.ini").write_text("[NETWORK]\n")
    (cluster / "Master" / "server.ini").write_text("[NETWORK]\n")
    if token_content is not None:
        (cluster / "cluster_token.txt").write_text(token_content)
    with pytest.raises(ServerError, match=r"ENABLED \(AUTH\): dstserver"):
        mod._assert_cluster_config_present(server)


def test_token_presence_is_validated_without_reading_or_logging_secret(tmp_path, capsys):
    from pathlib import Path
    from unittest.mock import patch
    server = DummyServer("dstauth")
    mod.configure(server, False, port=18000, dir=str(tmp_path))
    cluster = tmp_path / "DoNotStarveTogether" / server.name
    (cluster / "Master").mkdir(parents=True)
    (cluster / "cluster.ini").write_text("[NETWORK]\n")
    (cluster / "Master" / "server.ini").write_text("[NETWORK]\n")
    (cluster / "cluster_token.txt").write_text("private-provider-token")
    with patch.object(Path, "read_text", side_effect=AssertionError("Token must not be read")):
        mod._assert_cluster_config_present(server)
    assert "private-provider-token" not in repr(server.data)
    assert "private-provider-token" not in capsys.readouterr().out
