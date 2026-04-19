import json

import pytest

import gamemodules.minecraft.bungeecord as bungeecord
import gamemodules.minecraft.custom as custom
import utils.gamemodules.minecraft.properties_config as properties_config
import gamemodules.minecraft.vanilla as vanilla
import server.server as server_module
from utils.simple_kv_config import rewrite_equals_config

html5lib = pytest.importorskip("html5lib")
import gamemodules.minecraft.tekkit as tekkit


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


def test_custom_configure_sets_backup_defaults_and_returns_eula_state(tmp_path):
    server = DummyServer()

    args, kwargs = custom.configure(server, ask=False, port=25565, dir=str(tmp_path), eula=True)

    assert args == ()
    assert kwargs == {"eula": True}
    assert server.data["port"] == 25565
    assert server.data["dir"] == str(tmp_path)
    assert server.data["exe_name"] == "minecraft_server.jar"
    assert server.data["backup"]["profiles"]["default"]["targets"]
    assert server.data["backup"]["schedule"]


def test_custom_configure_uses_runtime_install_dir_helper(monkeypatch):
    server = DummyServer("mymc")

    observed = {}

    def fake_suggest_install_dir(current_server, current_dir=None):
        observed["current_dir"] = current_dir
        return "/srv/alphagsm/servers/" + current_server.name

    monkeypatch.setattr(custom.runtime_module, "suggest_install_dir", fake_suggest_install_dir)

    custom.configure(server, ask=False, port=25565, dir=None, eula=True)

    assert observed["current_dir"] is None
    assert server.data["dir"] == "/srv/alphagsm/servers/mymc"


def test_custom_configure_replaces_stale_manager_only_install_dir(monkeypatch):
    server = DummyServer("mymc")
    server.data["dir"] = "/root/mymc"

    observed = {}

    def fake_suggest_install_dir(current_server, current_dir=None):
        observed["current_dir"] = current_dir
        return "/srv/alphagsm/servers/" + current_server.name

    monkeypatch.setattr(custom.runtime_module, "suggest_install_dir", fake_suggest_install_dir)

    custom.configure(server, ask=False, port=25565, dir=None, eula=True)

    assert observed["current_dir"] == "/root/mymc"
    assert server.data["dir"] == "/srv/alphagsm/servers/mymc"


def test_custom_install_updates_generated_config_files(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "minecraft_server.jar", "port": 25565})
    (tmp_path / "minecraft_server.jar").write_text("")
    update_calls = []

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: update_calls.append((filename, settings)))
    monkeypatch.setattr(custom.sp, "check_call", lambda *args, **kwargs: 0)

    custom.install(server, eula=True)

    assert update_calls[0][0].endswith("server.properties")
    assert update_calls[0][1] == {
        "server-port": "25565",
        "gamemode": "survival",
        "difficulty": "easy",
        "level-name": "alpha",
        "max-players": "20",
        "motd": "AlphaGSM alpha",
    }
    assert update_calls[1][0].endswith("server.properties")
    assert update_calls[1][1] == {
        "server-port": "25565",
        "gamemode": "survival",
        "difficulty": "easy",
        "level-name": "alpha",
        "max-players": "20",
        "motd": "AlphaGSM alpha",
    }
    assert update_calls[2][0].endswith("eula.txt")
    assert update_calls[2][1] == {"eula": "true"}
    assert server.data.saved == 1


def test_custom_exposes_schema_metadata_for_native_properties():
    map_spec = custom.setting_schema["map"]
    servername_spec = custom.setting_schema["servername"]

    assert custom.config_sync_keys == (
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


def test_custom_uses_shared_properties_config_contract():
    assert custom.config_sync_keys == properties_config.CONFIG_SYNC_KEYS
    assert custom.setting_schema == properties_config.build_setting_schema(
        port_description="The port the server listens on.",
        port_example="25565",
        map_example="world",
        maxplayers_example="20",
        servername_description="The server name shown in the client list.",
        servername_example="AlphaGSM Server",
    )


def test_custom_uses_shared_equals_config_writer():
    assert custom.updateconfig is rewrite_equals_config


def test_custom_doset_servername_updates_motd_and_server_properties(monkeypatch, tmp_path):
    server = make_server(custom, "java")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 25565,
            "gamemode": "survival",
            "difficulty": "easy",
            "levelname": "world",
            "maxplayers": "20",
            "servername": "AlphaGSM Java",
        }
    )
    updates = []

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: updates.append((filename, settings)))

    server.doset("servername", "AlphaGSM Custom")

    assert server.data["servername"] == "AlphaGSM Custom"
    assert updates == [
        (
            str(tmp_path / "server.properties"),
            {
                "server-port": "25565",
                "gamemode": "survival",
                "difficulty": "easy",
                "level-name": "world",
                "max-players": "20",
                "motd": "AlphaGSM Custom",
            },
        )
    ]


def test_custom_doset_gamemap_updates_levelname_and_server_properties(monkeypatch, tmp_path):
    server = make_server(custom, "java")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 25565,
            "gamemode": "survival",
            "difficulty": "easy",
            "levelname": "world_one",
            "maxplayers": "20",
            "servername": "AlphaGSM Java",
        }
    )
    updates = []

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: updates.append((filename, settings)))

    server.doset("gamemap", "world_two")

    assert server.data["levelname"] == "world_two"
    assert updates == [
        (
            str(tmp_path / "server.properties"),
            {
                "server-port": "25565",
                "gamemode": "survival",
                "difficulty": "easy",
                "level-name": "world_two",
                "max-players": "20",
                "motd": "AlphaGSM Java",
            },
        )
    ]


def test_custom_install_writes_eula_before_first_boot(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "minecraft_server.jar", "port": 25565})
    (tmp_path / "minecraft_server.jar").write_text("")

    observed = {}

    def fake_check_call(*args, **kwargs):
        eula_path = tmp_path / "eula.txt"
        observed["exists"] = eula_path.exists()
        observed["content"] = eula_path.read_text(encoding="utf-8") if eula_path.exists() else ""
        (tmp_path / "server.properties").write_text("server-port=25565\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: None)
    monkeypatch.setattr(custom.sp, "check_call", fake_check_call)

    custom.install(server, eula=True)

    assert observed == {"exists": True, "content": "eula=true\n"}


def test_custom_message_sends_tellraw_to_all_players(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(
        custom.runtime_module,
        "send_to_server",
        lambda server_obj, payload: calls.append((server_obj.name, payload)),
    )

    custom.message(server, "Hello world")

    assert calls == [("hub", '\ntellraw @a {"text": "Hello world"}\n')]


def test_custom_message_parses_selectors_into_json_fragments(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(
        custom.runtime_module,
        "send_to_server",
        lambda server_obj, payload: calls.append(payload),
    )

    custom.message(server, r"Hi @p", "@a", parse=True)

    sent = calls[0]
    assert "tellraw @a" in sent
    assert json.dumps({"selector": "@p"}) in sent


def test_custom_checkvalue_handles_simple_and_backup_values(monkeypatch):
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {}}, "schedule": []}

    monkeypatch.setattr(custom.backups, "checkdatavalue", lambda data, key, *value: ["ok", key, value])

    assert custom.checkvalue(server, ("exe_name",), "server.jar") == "server.jar"
    assert custom.checkvalue(server, ("TEST",), "value") == "value"
    assert custom.checkvalue(server, ("backup", "profiles", "default"), "x") == ["ok", ("profiles", "default"), ("x",)]


def test_custom_checkvalue_accepts_server_properties_keys(monkeypatch):
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {}}, "schedule": []}

    monkeypatch.setattr(custom.backups, "checkdatavalue", lambda data, key, *value: ["ok", key, value])

    assert custom.checkvalue(server, ("port",), "25566") == 25566
    assert custom.checkvalue(server, ("gamemode",), "creative") == "creative"
    assert custom.checkvalue(server, ("difficulty",), "hard") == "hard"
    assert custom.checkvalue(server, ("maxplayers",), "30") == "30"
    assert custom.checkvalue(server, ("levelname",), "world") == "world"
    assert custom.checkvalue(server, ("servername",), "AlphaGSM Java") == "AlphaGSM Java"


def test_custom_sync_server_config_updates_server_properties(tmp_path, monkeypatch):
    server = DummyServer("java")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 25570,
            "gamemode": "creative",
            "difficulty": "hard",
            "levelname": "java_world",
            "maxplayers": "30",
            "servername": "AlphaGSM Java",
        }
    )
    update_calls = []

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: update_calls.append((filename, settings)))

    custom.sync_server_config(server)

    assert update_calls == [
        (
            str(tmp_path / "server.properties"),
                {
                    "server-port": "25570",
                    "gamemode": "creative",
                    "difficulty": "hard",
                    "level-name": "java_world",
                    "max-players": "30",
                    "motd": "AlphaGSM Java",
                },
            )
        ]


def test_custom_parsewhen_supports_all_frequencies(monkeypatch):
    monkeypatch.setattr(custom.random, "randint", lambda start, end: start)

    assert custom._parsewhen("daily", None) == (0, 2, None, None, None)
    assert custom._parsewhen("weekly", "12:30 fri") == ("30", "12", None, None, "fri")
    assert custom._parsewhen("monthly", "8 15") == (0, "8", "15", None, None)
    assert custom._parsewhen("yearly", "9:45 5/6") == ("45", "9", "5", "6", None)


def test_custom_op_and_deop_send_server_commands(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(
        custom.runtime_module,
        "send_to_server",
        lambda server_obj, payload: calls.append((server_obj.name, payload)),
    )

    custom.op(server, "alice", "bob")
    custom.deop(server, "alice")

    assert ("hub", "\nop alice\n") in calls
    assert ("hub", "\nop bob\n") in calls
    assert ("hub", "\ndeop alice\n") in calls


def test_dobackup_toggles_save_flags_around_backup(monkeypatch):
    server = DummyServer("hub")
    server.data.update({"dir": "/srv/mc", "backup": {"profiles": {"default": {"targets": []}}, "schedule": [("default", 0, "day")]}})
    calls = []

    monkeypatch.setattr(custom.runtime_module, "check_server_running", lambda server_obj: True)
    monkeypatch.setattr(
        custom.runtime_module,
        "send_to_server",
        lambda server_obj, payload: calls.append((server_obj.name, payload)),
    )
    monkeypatch.setattr(custom.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(custom.backups, "backup", lambda dir_path, backup_data, profile: calls.append(("backup", dir_path, profile)))

    custom.dobackup(server, profile="default")

    assert calls[0] == ("hub", "\nsave-off\nsave-all\n")
    assert ("backup", "/srv/mc", "default") in calls
    assert calls[-1] == ("hub", "\nsave-on\nsave-all\n")


def test_custom_runtime_requirements_include_java_mounts_and_ports():
    server = DummyServer("hub")
    server.data.update(
        {
            "dir": "/srv/minecraft",
            "exe_name": "minecraft_server.jar",
            "port": 25565,
            "version": "1.20.6",
        }
    )

    requirements = custom.get_runtime_requirements(server)
    spec = custom.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "java"
    assert requirements["java"] == 21
    assert requirements["env"]["ALPHAGSM_SERVER_JAR"] == "minecraft_server.jar"
    assert requirements["mounts"] == [
        {"source": "/srv/minecraft", "target": "/srv/server", "mode": "rw"}
    ]
    assert requirements["ports"] == [
        {"host": 25565, "container": 25565, "protocol": "tcp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][-1] == 'exec java -jar "$ALPHAGSM_SERVER_JAR" nogui'


def test_bungeecord_configure_install_and_checkvalue(tmp_path):
    server = DummyServer()

    args, kwargs = bungeecord.configure(server, ask=False, dir=str(tmp_path))
    (tmp_path / "BungeeCord.jar").write_text("")
    bungeecord.install(server)

    assert args == ()
    assert kwargs == {}
    assert server.data["dir"] == str(tmp_path)
    assert bungeecord.get_start_command(server) == (["java", "-Xmx256M", "-jar", "BungeeCord.jar"], str(tmp_path))
    assert bungeecord.checkvalue(server, "exe_name", "proxy.jar") == "proxy.jar"


def test_bungeecord_configure_uses_runtime_install_dir_helper(monkeypatch):
    server = DummyServer("proxy")

    observed = {}

    def fake_suggest_install_dir(current_server, current_dir=None):
        observed["current_dir"] = current_dir
        return "/srv/alphagsm/servers/" + current_server.name

    monkeypatch.setattr(
        bungeecord.runtime_module,
        "suggest_install_dir",
        fake_suggest_install_dir,
    )

    bungeecord.configure(server, ask=False, dir=None)

    assert observed["current_dir"] is None
    assert server.data["dir"] == "/srv/alphagsm/servers/proxy"


def test_bungeecord_configure_replaces_stale_manager_only_install_dir(monkeypatch):
    server = DummyServer("proxy")
    server.data["dir"] = "/root/proxy"

    observed = {}

    def fake_suggest_install_dir(current_server, current_dir=None):
        observed["current_dir"] = current_dir
        return "/srv/alphagsm/servers/" + current_server.name

    monkeypatch.setattr(
        bungeecord.runtime_module,
        "suggest_install_dir",
        fake_suggest_install_dir,
    )

    bungeecord.configure(server, ask=False, dir=None)

    assert observed["current_dir"] == "/root/proxy"
    assert server.data["dir"] == "/srv/alphagsm/servers/proxy"


def test_bungeecord_install_requires_existing_jar(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "BungeeCord.jar"})

    with pytest.raises(bungeecord.ServerError, match="Can't find server jar"):
        bungeecord.install(server)


def test_bungeecord_updates_unindented_host_line(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text("host: 0.0.0.0:25577\n", encoding="utf-8")

    bungeecord._update_bungee_host_port(str(config_path), 31234)

    assert config_path.read_text(encoding="utf-8") == "host: 0.0.0.0:31234\n"


def test_bungeecord_install_waits_for_generated_config_and_rewrites_port(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "BungeeCord.jar", "port": 31234})
    (tmp_path / "BungeeCord.jar").write_text("")
    config_path = tmp_path / "config.yml"

    class FakeProc:
        def __init__(self):
            self.poll_count = 0

        def poll(self):
            self.poll_count += 1
            if self.poll_count == 3:
                config_path.write_text("host: 0.0.0.0:25577\n", encoding="utf-8")
            return None if self.poll_count < 4 else 0

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(bungeecord.sp, "Popen", lambda *args, **kwargs: FakeProc())
    monkeypatch.setattr(bungeecord.time, "sleep", lambda seconds: None)

    bungeecord.install(server)

    assert config_path.read_text(encoding="utf-8") == "host: 0.0.0.0:31234\n"


def test_bungeecord_runtime_requirements_use_java_family():
    server = DummyServer("proxy")
    server.data.update({"dir": "/srv/proxy", "exe_name": "BungeeCord.jar", "port": 25577})

    requirements = bungeecord.get_runtime_requirements(server)
    spec = bungeecord.get_container_spec(server)

    assert requirements["family"] == "java"
    assert requirements["java"] == 17
    assert requirements["env"]["ALPHAGSM_SERVER_JAR"] == "BungeeCord.jar"
    assert requirements["ports"] == [
        {"host": 25577, "container": 25577, "protocol": "tcp"}
    ]
    assert spec["command"][-1] == 'exec java -Xmx256M -jar "$ALPHAGSM_SERVER_JAR"'


def test_bungeecord_query_and_info_addresses_use_runtime_query_host(monkeypatch):
    server = DummyServer("proxy")
    server.data["port"] = 25577
    monkeypatch.setattr(bungeecord.runtime_module, "resolve_query_host", lambda srv: "172.18.0.9")

    assert bungeecord.get_query_address(server) == ("172.18.0.9", 25577, "tcp")
    assert bungeecord.get_info_address(server) == ("172.18.0.9", 25577, "slp")


def test_custom_query_and_info_addresses_use_runtime_query_host(monkeypatch):
    server = DummyServer("vanilla")
    server.data["port"] = 25565
    monkeypatch.setattr(custom.runtime_module, "resolve_query_host", lambda srv: "172.18.0.10")

    assert custom.get_query_address(server) == ("172.18.0.10", 25565, "tcp")
    assert custom.get_info_address(server) == ("172.18.0.10", 25565, "slp")


def test_vanilla_runtime_wrappers_use_java_family():
    server = DummyServer("vanilla")
    server.data.update(
        {
            "dir": "/srv/vanilla",
            "exe_name": "minecraft_server.jar",
            "port": 25565,
            "version": "1.20.6",
        }
    )

    requirements = vanilla.get_runtime_requirements(server)
    spec = vanilla.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "java"
    assert requirements["java"] == 21
    assert requirements["env"]["ALPHAGSM_SERVER_JAR"] == "minecraft_server.jar"
    assert requirements["ports"] == [
        {"host": 25565, "container": 25565, "protocol": "tcp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][:6] == ["java", "-jar", "minecraft_server.jar", "nogui", "--port", "25565"]


def test_custom_start_command_passes_explicit_port():
    server = DummyServer("vanilla")
    server.data.update(
        {
            "dir": "/srv/vanilla",
            "exe_name": "minecraft_server.jar",
            "port": 25565,
        }
    )

    command, cwd = custom.get_start_command(server)

    assert cwd == "/srv/vanilla"
    assert command == ["java", "-jar", "minecraft_server.jar", "nogui", "--port", "25565"]


def test_tekkit_runtime_wrappers_use_java_family():
    server = DummyServer("tekkit")
    server.data.update(
        {
            "dir": "/srv/tekkit",
            "exe_name": "Tekkit.jar",
            "port": 25566,
            "version": "1.12.2",
        }
    )

    requirements = tekkit.get_runtime_requirements(server)
    spec = tekkit.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "java"
    assert requirements["java"] == 8
    assert requirements["env"]["ALPHAGSM_SERVER_JAR"] == "Tekkit.jar"
    assert requirements["ports"] == [
        {"host": 25566, "container": 25566, "protocol": "tcp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][:5] == ["java", "-Xmx3G", "-Xms2G", "-jar", "Tekkit.jar"]


def test_vanilla_configure_prefers_explicit_version_url_and_download_metadata(tmp_path, monkeypatch):
    server = DummyServer()
    responses = {
        vanilla.VERSION_MANIFEST_URL: {
            "latest": {"release": "1.20.4"},
            "versions": [
                {
                    "id": "1.20.4",
                    "type": "release",
                    "url": "https://piston-meta.mojang.com/v1/packages/example-1.20.4.json",
                }
            ],
        },
        "https://piston-meta.mojang.com/v1/packages/example-1.20.4.json": {
            "downloads": {"server": {"url": "https://example.com/minecraft_server.1.20.4.jar"}}
        },
    }

    monkeypatch.setattr(
        vanilla.urllib.request,
        "urlopen",
        lambda url: type(
            "Response", (), {"read": lambda self: json.dumps(responses[url]).encode("utf-8")}
        )(),
    )
    captured = {}
    monkeypatch.setattr(vanilla.cust, "configure", lambda server_obj, ask, port, dir, eula=None, exe_name=None: captured.update({"port": port, "dir": dir, "eula": eula, "exe_name": exe_name}) or ((), {"eula": eula}))

    args, kwargs = vanilla.configure(server, ask=False, port=25565, dir=str(tmp_path), version="1.20.4")

    assert args == ()
    assert kwargs == {"eula": None}
    assert server.data["version"] == "1.20.4"
    assert server.data["url"] == "https://example.com/minecraft_server.1.20.4.jar"
    assert server.data["download_name"] == "minecraft_server.jar"
    assert captured["exe_name"] == "minecraft_server.jar"


def test_vanilla_install_downloads_and_symlinks_plain_jar(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "minecraft_server.jar",
            "download_name": "minecraft_server.jar",
            "url": "http://example.com/server.jar",
        }
    )
    target_download = tmp_path / "downloaded"
    target_download.mkdir()
    (target_download / "minecraft_server.jar").write_text("")
    symlinks = []

    monkeypatch.setattr(vanilla.downloader, "getpath", lambda module, args: str(target_download))
    monkeypatch.setattr(vanilla.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(vanilla.os, "symlink", lambda src, dst: symlinks.append((src, dst)))
    monkeypatch.setattr(vanilla.cust, "install", lambda server_obj, eula=False: symlinks.append(("install", eula)))

    vanilla.install(server, eula=True)

    assert symlinks[0] == (str(target_download / "minecraft_server.jar"), str(tmp_path / "minecraft_server.jar"))
    assert symlinks[1] == ("install", True)
    assert server.data["current_url"] == server.data["url"]


def test_tekkit_get_file_url_returns_first_server_download(monkeypatch):
    class FakeAnchor:
        def __init__(self, href, text):
            self._href = href
            self._text = text

        def get(self, key):
            return self._href

        def itertext(self):
            return [self._text]

    class FakeBody:
        def iter(self, tag):
            return iter(
                [
                    FakeAnchor("http://example.com/ignore", "Client Download"),
                    FakeAnchor("http://example.com/server.zip", "Server Download"),
                ]
            )

    class FakeDom:
        tag = "{x}html"

        def find(self, tag):
            return FakeBody()

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    monkeypatch.setattr(tekkit.urllib.request, "urlopen", lambda url: FakeResponse())
    monkeypatch.setattr(tekkit.html5lib, "parse", lambda file_obj, parser: FakeDom())

    assert tekkit.get_file_url("http://example.com/modpack") == "http://example.com/server.zip"
