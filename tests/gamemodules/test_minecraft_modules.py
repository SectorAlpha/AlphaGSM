import json

import pytest

import gamemodules.minecraft.bungeecord as bungeecord
import gamemodules.minecraft.custom as custom
import gamemodules.minecraft.vanilla as vanilla

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


def test_custom_install_updates_generated_config_files(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "minecraft_server.jar", "port": 25565})
    (tmp_path / "minecraft_server.jar").write_text("")
    update_calls = []

    monkeypatch.setattr(custom, "updateconfig", lambda filename, settings: update_calls.append((filename, settings)))
    monkeypatch.setattr(custom.sp, "check_call", lambda *args, **kwargs: 0)

    custom.install(server, eula=True)

    assert update_calls[0][0].endswith("server.properties")
    assert update_calls[0][1] == {"server-port": "25565"}
    assert update_calls[1][0].endswith("eula.txt")
    assert update_calls[1][1] == {"eula": "true"}
    assert server.data.saved == 1


def test_custom_message_sends_tellraw_to_all_players(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(custom.screen, "send_to_server", lambda name, payload: calls.append((name, payload)))

    custom.message(server, "Hello world")

    assert calls == [("hub", '\ntellraw @a {"text": "Hello world"}\n')]


def test_custom_message_parses_selectors_into_json_fragments(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(custom.screen, "send_to_server", lambda name, payload: calls.append(payload))

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


def test_custom_parsewhen_supports_all_frequencies(monkeypatch):
    monkeypatch.setattr(custom.random, "randint", lambda start, end: start)

    assert custom._parsewhen("daily", None) == (0, 2, None, None, None)
    assert custom._parsewhen("weekly", "12:30 fri") == ("30", "12", None, None, "fri")
    assert custom._parsewhen("monthly", "8 15") == (0, "8", "15", None, None)
    assert custom._parsewhen("yearly", "9:45 5/6") == ("45", "9", "5", "6", None)


def test_custom_op_and_deop_send_server_commands(monkeypatch):
    server = DummyServer("hub")
    calls = []

    monkeypatch.setattr(custom.screen, "send_to_server", lambda name, payload: calls.append((name, payload)))

    custom.op(server, "alice", "bob")
    custom.deop(server, "alice")

    assert ("hub", "\nop alice\n") in calls
    assert ("hub", "\nop bob\n") in calls
    assert ("hub", "\ndeop alice\n") in calls


def test_dobackup_toggles_save_flags_around_backup(monkeypatch):
    server = DummyServer("hub")
    server.data.update({"dir": "/srv/mc", "backup": {"profiles": {"default": {"targets": []}}, "schedule": [("default", 0, "day")]}})
    calls = []

    monkeypatch.setattr(custom.screen, "check_screen_exists", lambda name: True)
    monkeypatch.setattr(custom.screen, "send_to_server", lambda name, payload: calls.append((name, payload)))
    monkeypatch.setattr(custom.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(custom.backups, "backup", lambda dir_path, backup_data, profile: calls.append(("backup", dir_path, profile)))

    custom.dobackup(server, profile="default")

    assert calls[0] == ("hub", "\nsave-off\nsave-all\n")
    assert ("backup", "/srv/mc", "default") in calls
    assert calls[-1] == ("hub", "\nsave-on\nsave-all\n")


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


def test_bungeecord_install_requires_existing_jar(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "BungeeCord.jar"})

    with pytest.raises(bungeecord.ServerError, match="Can't find server jar"):
        bungeecord.install(server)


def test_vanilla_configure_prefers_explicit_version_url_and_download_metadata(tmp_path, monkeypatch):
    server = DummyServer()
    monkeypatch.setattr(vanilla.urllib.request, "urlopen", lambda url: type("Response", (), {"read": lambda self: b'{"latest":{"release":"1.20.4"},"versions":[{"id":"1.20.4","type":"release"}]}'})())
    captured = {}
    monkeypatch.setattr(vanilla.cust, "configure", lambda server_obj, ask, port, dir, eula=None, exe_name=None: captured.update({"port": port, "dir": dir, "eula": eula, "exe_name": exe_name}) or ((), {"eula": eula}))

    args, kwargs = vanilla.configure(server, ask=False, port=25565, dir=str(tmp_path), version="1.20.4")

    assert args == ()
    assert kwargs == {"eula": None}
    assert server.data["version"] == "1.20.4"
    assert server.data["url"].endswith("/1.20.4/minecraft_server.1.20.4.jar")
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

    monkeypatch.setattr(tekkit.urllib.request, "urlopen", lambda url: object())
    monkeypatch.setattr(tekkit.html5lib, "parse", lambda file_obj, parser: FakeDom())

    assert tekkit.get_file_url("http://example.com/modpack") == "http://example.com/server.zip"
