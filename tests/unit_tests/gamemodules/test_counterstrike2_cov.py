"""Full coverage tests for counterstrike2."""

from pathlib import Path
from unittest.mock import MagicMock, patch

sys_modules_patch = {
    "downloader": MagicMock(),
    "screen": MagicMock(),
    "utils.backups": MagicMock(),
    "utils.backups.backups": MagicMock(),
    "utils.fileutils": MagicMock(),
}

with patch.dict("sys.modules", sys_modules_patch):
    import gamemodules.counterstrike2 as mod


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="testserver"):
        self.name = name
        self.data = DummyData()


def test_configure_sets_expected_defaults(tmp_path):
    server = DummyServer()

    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 730
    assert server.data["Steam_anonymous_login_possible"] is True
    assert server.data["exe_name"] == "game/cs2.sh"
    assert server.data["startmap"] == "de_dust2"
    assert server.data["port"] == 27015
    assert server.data["dir"].endswith("/")
    assert server.data.saved == 1


def test_command_args_expose_setup_update_and_restart():
    assert "setup" in mod.command_args
    assert "update" in mod.command_args
    assert "restart" in mod.command_args
    assert mod.command_args["setup"].optionalarguments[0].name == "PORT"
    assert mod.command_args["setup"].optionalarguments[1].name == "DIR"
    assert mod.command_args["update"].options[0].keyword == "validate"
    assert mod.command_args["update"].options[1].keyword == "restart"


def test_install_creates_default_server_config(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "Steam_AppID": 730,
            "Steam_anonymous_login_possible": True,
            "exe_name": "game/cs2.sh",
        }
    )
    cfg_path = tmp_path / "game" / "csgo" / "cfg" / "server.cfg"
    calls = []

    monkeypatch.setattr(mod, "doinstall", lambda server_obj: calls.append(server_obj))
    monkeypatch.setattr(
        mod,
        "make_empty_file",
        lambda path: Path(path).parent.mkdir(parents=True, exist_ok=True) or Path(path).write_text(""),
    )

    mod.install(server)

    assert calls == [server]
    assert cfg_path.exists()


def test_doinstall_uses_non_validating_first_download(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "Steam_AppID": 730,
            "Steam_anonymous_login_possible": True,
        }
    )
    calls = []

    monkeypatch.setattr(
        mod.steamcmd,
        "download",
        lambda path, app_id, anonymous, validate=False: calls.append(
            (path, app_id, anonymous, validate)
        ),
    )

    mod.doinstall(server)

    assert calls == [(server.data["dir"], 730, True, False)]


def test_get_start_command_uses_default_launcher(tmp_path):
    server = DummyServer()
    launcher = tmp_path / "game" / "cs2.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "game/cs2.sh",
            "port": 27015,
            "startmap": "de_dust2",
            "maxplayers": "24",
        }
    )

    command, cwd = mod.get_start_command(server)

    assert command[0] == "./game/cs2.sh"
    assert "-dedicated" in command
    assert "+map" in command
    assert cwd == server.data["dir"]


def test_get_query_and_info_addresses_use_source_query_address(monkeypatch):
    server = DummyServer("cs2")
    server.data["port"] = 27015
    calls = []
    monkeypatch.setattr(mod, "source_query_address", lambda srv: calls.append(srv) or ("127.0.0.1", 27015, "a2s"))

    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "a2s")
    assert calls == [server, server]


def test_do_stop_uses_runtime_send_to_server(monkeypatch):
    server = DummyServer("cs2")
    calls = []

    monkeypatch.setattr(mod.runtime_module, "send_to_server", lambda srv, text: calls.append((srv, text)))

    mod.do_stop(server, 0)

    assert calls == [(server, "\nquit\n")]


def test_runtime_requirements_and_container_spec_use_steamcmd_linux_family(tmp_path):
    server = DummyServer("cs2")
    launcher = tmp_path / "game" / "cs2.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "game/cs2.sh",
            "port": 27015,
            "startmap": "de_dust2",
            "maxplayers": "24",
        }
    )

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "tcp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./game/cs2.sh"
