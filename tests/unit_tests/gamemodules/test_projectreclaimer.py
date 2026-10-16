"""Contract coverage without claiming a real MCC lifecycle pass."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from server.module_contract import validate_module_contract
from server.settable_keys import resolve_requested_key


class Data(dict):
    def save(self):
        pass


@pytest.fixture
def game(tmp_path):
    from gamemodules import projectreclaimer as module
    server = SimpleNamespace(name="halo", data=Data(), module=module)
    module.configure(server, False, 49176, str(tmp_path / "server"))
    return module, server


def test_public_contract_and_config_sync(game):
    module, server = game
    validate_module_contract("projectreclaimer", module)
    module.sync_server_config(server)
    path = Path(server.data["dir"]) / "dedicated.toml"
    text = path.read_text()
    assert 'enabled = false' in text
    assert 'port = 49176' in text
    assert 'rcon_port = 49177' in text
    assert len(server.data["rconpassword"]) >= 32
    assert 'password' not in module.get_asset_requirements(server)["include"]
    path.write_text(text + '\n# custom settings survive\ncustom_setting = true\n')
    server.data["servername"] = 'Friends "Halo"'
    module.sync_server_config(server)
    assert '# custom settings survive' in path.read_text()
    assert 'Friends \\"Halo\\"' in path.read_text()
    assert path.read_text().count("[master]") == 1
    assert path.read_text().count("[rcon]") == 1
    assert path.read_text().count("[[server]]") == 1


def test_map_validation_and_asset_recipe(game):
    module, server = game
    with pytest.raises(ServerError, match="map"):
        module.checkvalue(server, "map", "../../escape")
    assert module.checkvalue(server, "maxplayers", "127") == 127
    with pytest.raises(ServerError):
        module.checkvalue(server, "maxplayers", "128")
    recipe = module.get_asset_requirements(server)
    assert recipe["target"] == "game"
    assert "halo3/maps/shared.map" in recipe["required"]
    assert "halo3/maps/guardian.map" in recipe["required"]
    assert resolve_requested_key("hostname", module.setting_schema).canonical_key == "servername"


def test_config_comments_and_pinned_updates_remain_valid(game):
    module, server = game
    root = Path(server.data["dir"])
    root.mkdir(parents=True)
    path = root / "dedicated.toml"
    path.write_text('auto_update = true\n[master] # keep this comment\nenabled = true\n')
    module.sync_server_config(server)
    assert 'auto_update = false' in path.read_text()
    assert path.read_text().count('[master]') == 1


def test_unicode_config_and_local_rcon_address(game):
    module, server = game
    server.data.update(servername="Halo 🚀", publicip="192.0.2.1")
    module.sync_server_config(server)
    text = (Path(server.data["dir"]) / "dedicated.toml").read_text(encoding="utf-8")
    assert "\\ud83d" not in text
    assert module.get_query_address(server)[0] == "127.0.0.1"


def test_rcon_command_prints_response(game, monkeypatch, capsys):
    module, server = game
    monkeypatch.setattr(module.reclaimer, "command", lambda *args: {"text": "0/16 players"})
    module.rcon(server, "status")
    assert "0/16 players" in capsys.readouterr().out


@pytest.mark.parametrize("key,value,expected", [
    ("map", "Guardian", "Guardian"), ("maxplayers", "32", 32),
    ("port", "49180", 49180), ("rconpassword", "new-private-password", "new-private-password"),
])
def test_set_uses_real_parsed_key_paths(game, key, value, expected):
    module, server = game
    assert module.checkvalue(server, [key], value) == expected


def test_real_server_set_updates_managed_values(game, monkeypatch):
    from server.server import Server
    from server import port_manager
    module, original = game
    server = Server.__new__(Server)
    server.name, server.data, server.module = original.name, original.data, module
    monkeypatch.setattr(port_manager, "detect_conflicts", lambda _server: [])
    for key, value in (("map", "Guardian"), ("maxplayers", "32"), ("rconpassword", "new-private-password"),
                       ("hostname", "Friends"), ("port", "49180")):
        server.doset(key, value)
    assert server.data["maxplayers"] == 32
    assert server.data["servername"] == "Friends"
    assert server.data["port"] == 49180
    text = (Path(server.data["dir"]) / "dedicated.toml").read_text()
    assert "max_players = 32" in text and "port = 49180" in text


def test_relative_setup_directory_is_stored_as_absolute(tmp_path, monkeypatch):
    from gamemodules import projectreclaimer as module
    monkeypatch.chdir(tmp_path)
    server = SimpleNamespace(name="halo", data=Data())
    module.configure(server, False, 49176, "servers/halo")
    assert Path(server.data["dir"]).is_absolute()


@pytest.mark.parametrize("port", [1, 65536])
def test_setup_rejects_invalid_ports(tmp_path, port):
    from gamemodules import projectreclaimer as module
    with pytest.raises(ServerError, match="port"):
        module.configure(SimpleNamespace(name="halo", data=Data()), False, port, str(tmp_path))


def test_config_updates_instance_rcon_override(game):
    module, server = game
    root = Path(server.data["dir"])
    root.mkdir(parents=True)
    path = root / "dedicated.toml"
    path.write_text('[[server]]\nrcon_password = "old-password"\n')
    module.sync_server_config(server)
    assert 'rcon_password = ' + json.dumps(server.data["rconpassword"]) in path.read_text()


@pytest.mark.parametrize("selection", ['playlist = "rotation.json"', 'variant = "custom"', 'campaign = "Sierra 117"'])
def test_unsupported_selection_is_rejected_without_changing_config(game, selection):
    module, server = game
    root = Path(server.data["dir"])
    root.mkdir(parents=True)
    path = root / "dedicated.toml"
    original = '[[server]]\n' + selection + '\n'
    path.write_text(original)
    with pytest.raises(ServerError, match="selection"):
        module.sync_server_config(server)
    assert path.read_text() == original


def test_native_and_container_contract(game, monkeypatch):
    module, server = game
    root = Path(server.data["dir"])
    root.mkdir(parents=True)
    (root / "project-reclaimer.exe").write_bytes(b"MZfixture")
    monkeypatch.setattr(module, "IS_LINUX", False)
    command, cwd = module.get_start_command(server)
    assert command == [str(root / "project-reclaimer.exe"), "dedicated"]
    assert cwd == str(root)
    requirements = module.get_runtime_requirements(server)
    assert requirements["family"] == "wine-proton"
    spec = module.get_container_spec(server)
    assert spec["stop_signal"] == "SIGINT"
    assert spec["stop_timeout"] == 30
    assert spec["network_mode"] == "host"
    assert any(m["mode"] == "ro" and m["target"].endswith("/game") for m in spec["mounts"])
    assert spec["command"][-1] == "dedicated"


def test_download_is_checksum_pinned_and_repeated_setup_is_offline(game, monkeypatch):
    module, server = game
    calls = []

    def download(url, *, allowed_hosts, target_path, checksum):
        calls.append((url, checksum))
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MZfixture")
        return path

    monkeypatch.setattr(module, "download_to_cache", download)
    monkeypatch.setattr(module, "_sha256", lambda path: module.SERVER_SHA256)
    module.install(server)
    module.install(server)
    assert len(calls) == 1
    assert calls[0][1] == module.SERVER_SHA256
    assert "/v0.9.18/" in calls[0][0]
    assert (Path(server.data["dir"]) / "dedicated.toml").exists()


def test_missing_assets_explain_the_import_command(game):
    module, server = game
    with pytest.raises(ServerError, match="assets"):
        module.prestart(server)


def test_query_and_info_use_real_rcon_metadata(game, monkeypatch, capsys):
    from server.server import Server
    from utils import reclaimer
    module, server = game
    monkeypatch.setattr(reclaimer, "server_info", lambda *a, **kw: {
        "name": "Friends", "map": "Guardian", "players": 0, "max_players": 16,
    })
    Server.query(server)
    assert "Server is responding" in capsys.readouterr().out
    Server.info(server, as_json=True)
    report = json.loads(capsys.readouterr().out)
    assert report["protocol"] == "reclaimer_rcon"
    assert report["map"] == "Guardian"
    assert server.data["rconpassword"] not in json.dumps(report)
