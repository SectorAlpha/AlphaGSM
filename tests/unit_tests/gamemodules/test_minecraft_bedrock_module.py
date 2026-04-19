import pytest

import gamemodules.minecraft.bedrock as bedrock
import utils.gamemodules.minecraft.properties_config as properties_config
import server.server as server_module
from utils.simple_kv_config import rewrite_equals_config


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="alpha"):
        self.name = name
        self.data = DummyData()


def make_server(module, name="alpha"):
    server = server_module.Server.__new__(server_module.Server)
    server.name = name
    server.module = module
    server.data = DummyData()
    return server


def test_resolve_bedrock_download_uses_explicit_version():
    version, url = bedrock.resolve_bedrock_download("1.21.100.6")

    assert version == "1.21.100.6"
    assert url.endswith("/bedrock-server-1.21.100.6.zip")


def test_resolve_bedrock_download_parses_latest_page(monkeypatch):
    monkeypatch.setattr(
        bedrock,
        "_read_download_page",
        lambda: '<a href="https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-1.21.100.6.zip">download</a>',
    )

    version, url = bedrock.resolve_bedrock_download()

    assert version == "1.21.100.6"
    assert url.endswith("/bedrock-server-1.21.100.6.zip")


def test_bedrock_configure_sets_defaults(tmp_path, monkeypatch):
    server = DummyServer("bedrock")
    monkeypatch.setattr(
        bedrock,
        "resolve_bedrock_download",
        lambda version=None: ("1.21.100.6", "http://example.com/bedrock.zip"),
    )

    args, kwargs = bedrock.configure(server, ask=False, port=19132, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["url"] == "http://example.com/bedrock.zip"
    assert server.data["backupfiles"] == [
        "worlds",
        "server.properties",
        "permissions.json",
        "allowlist.json",
    ]
    assert server.data["levelname"] == "bedrock"
    assert server.data["exe_name"] == "bedrock_server"


def test_bedrock_configure_uses_runtime_install_dir_helper(monkeypatch):
    server = DummyServer("bedrock")
    monkeypatch.setattr(
        bedrock,
        "resolve_bedrock_download",
        lambda version=None: ("1.21.100.6", "http://example.com/bedrock.zip"),
    )
    monkeypatch.setattr(
        bedrock.runtime_module,
        "suggest_install_dir",
        lambda current_server, current_dir=None: "/srv/alphagsm/servers/" + current_server.name,
    )

    bedrock.configure(server, ask=False, dir=None)

    assert server.data["dir"] == "/srv/alphagsm/servers/bedrock"


def test_bedrock_install_downloads_archive_and_updates_properties(tmp_path, monkeypatch):
    server = DummyServer("bedrock")
    server.data.update(
        {
            "dir": str(tmp_path / "server"),
            "exe_name": "bedrock_server",
            "url": "http://example.com/bedrock.zip",
            "download_name": "bedrock-server.zip",
            "port": 19132,
            "gamemode": "creative",
            "difficulty": "hard",
            "levelname": "world_one",
            "maxplayers": "12",
            "servername": "AlphaGSM Bedrock",
        }
    )
    download_root = tmp_path / "download"
    executable = download_root / "bedrock_server"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    updates = []

    monkeypatch.setattr(bedrock.downloader, "getpath", lambda module, args: str(download_root))
    monkeypatch.setattr(bedrock, "updateconfig", lambda filename, settings: updates.append((filename, settings)))

    bedrock.install(server)

    assert (tmp_path / "server" / "bedrock_server").exists()
    assert updates[0][0].endswith("server.properties")
    assert updates[0][1]["server-port"] == "19132"
    assert updates[0][1]["level-name"] == "world_one"
    assert updates[0][1]["server-name"] == "AlphaGSM Bedrock"
    assert server.data["current_url"] == "http://example.com/bedrock.zip"


def test_bedrock_doset_gamemap_updates_levelname_and_server_properties(monkeypatch, tmp_path):
    server = make_server(bedrock, "bedrock")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 19132,
            "gamemode": "survival",
            "difficulty": "easy",
            "levelname": "world_one",
            "maxplayers": "10",
            "servername": "AlphaGSM Bedrock",
        }
    )
    updates = []

    monkeypatch.setattr(bedrock, "updateconfig", lambda filename, settings: updates.append((filename, settings)))

    server.doset("gamemap", "world_two")

    assert server.data["levelname"] == "world_two"
    assert updates == [
        (
            str(tmp_path / "server.properties"),
            {
                "server-port": "19132",
                "gamemode": "survival",
                "difficulty": "easy",
                "level-name": "world_two",
                "max-players": "10",
                "server-name": "AlphaGSM Bedrock",
            },
        )
    ]


def test_bedrock_exposes_schema_metadata_for_native_properties():
    map_spec = bedrock.setting_schema["map"]
    servername_spec = bedrock.setting_schema["servername"]

    assert bedrock.config_sync_keys == (
        "port",
        "gamemode",
        "difficulty",
        "levelname",
        "maxplayers",
        "servername",
    )
    assert map_spec.canonical_key == "map"
    assert map_spec.aliases == ("gamemap", "level", "world")
    assert map_spec.storage_key == "levelname"
    assert servername_spec.canonical_key == "servername"
    assert servername_spec.aliases == ()


def test_bedrock_uses_shared_properties_config_contract():
    assert bedrock.config_sync_keys == properties_config.CONFIG_SYNC_KEYS
    assert bedrock.setting_schema == properties_config.build_setting_schema(
        port_description="The port the Bedrock server listens on.",
        port_example="19132",
        map_example="Bedrock level",
        maxplayers_example="10",
        servername_description="The server name shown in Bedrock server listings.",
        servername_example="AlphaGSM Bedrock Server",
    )


def test_bedrock_uses_shared_equals_config_writer():
    assert bedrock.updateconfig is rewrite_equals_config


def test_bedrock_sync_server_config_updates_server_properties(monkeypatch, tmp_path):
    server = DummyServer("bedrock")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 19133,
            "gamemode": "creative",
            "difficulty": "hard",
            "levelname": "world_two",
            "maxplayers": "20",
            "servername": "AlphaGSM Changed",
        }
    )
    updates = []

    monkeypatch.setattr(bedrock, "updateconfig", lambda filename, settings: updates.append((filename, settings)))

    bedrock.sync_server_config(server)

    assert updates == [
        (
            str(tmp_path / "server.properties"),
            {
                "server-port": "19133",
                "gamemode": "creative",
                "difficulty": "hard",
                "level-name": "world_two",
                "max-players": "20",
                "server-name": "AlphaGSM Changed",
            },
        )
    ]


def test_bedrock_sync_server_config_requires_existing_gamemode(tmp_path):
    server = DummyServer("bedrock")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 19133,
            "difficulty": "hard",
            "levelname": "world_two",
            "maxplayers": "20",
            "servername": "AlphaGSM Changed",
        }
    )

    with pytest.raises(KeyError):
        bedrock.sync_server_config(server)


def test_bedrock_get_start_command_uses_local_library_path(tmp_path):
    server = DummyServer("bedrock")
    executable = tmp_path / "bedrock_server"
    executable.write_text("")
    server.data.update({"dir": str(tmp_path), "exe_name": "bedrock_server"})

    cmd, cwd = bedrock.get_start_command(server)

    assert cmd == ["env", "LD_LIBRARY_PATH=.", "./bedrock_server"]
    assert cwd == str(tmp_path)
