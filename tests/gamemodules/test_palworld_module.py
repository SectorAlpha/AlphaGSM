import gamemodules.palworld as palworld


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
        self.stop_calls = 0
        self.start_calls = 0

    def stop(self):
        self.stop_calls += 1

    def start(self):
        self.start_calls += 1


def test_palworld_configure_sets_defaults(tmp_path):
    server = DummyServer("palalpha")

    args, kwargs = palworld.configure(server, ask=False, port=8211, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == 2394010
    assert server.data["port"] == 8211
    assert server.data["backupfiles"] == ["Pal/Saved", "PalWorldSettings.ini", "PalServer.sh"]
    assert server.data["publiclobby"] is False


def test_palworld_install_copies_default_settings(tmp_path, monkeypatch):
    server = DummyServer("palalpha")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "Steam_AppID": 2394010,
            "Steam_anonymous_login_possible": True,
        }
    )
    default_settings = tmp_path / "DefaultPalWorldSettings.ini"
    default_settings.write_text("Default")
    calls = []

    monkeypatch.setattr(
        palworld.steamcmd,
        "download",
        lambda path, app_id, anon, validate=False: calls.append((path, app_id, anon, validate)),
    )

    palworld.install(server)

    active_settings = tmp_path / "Pal" / "Saved" / "Config" / "LinuxServer" / "PalWorldSettings.ini"
    assert calls == [(str(tmp_path) + "/", 2394010, True, False)]
    assert active_settings.read_text() == "Default"


def test_palworld_get_start_command_supports_community_flag(tmp_path):
    server = DummyServer("palalpha")
    exe = tmp_path / "PalServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "PalServer.sh", "publiclobby": True})

    cmd, cwd = palworld.get_start_command(server)

    assert cmd == ["./PalServer.sh", "-publiclobby"]
    assert cwd == server.data["dir"]


def test_palworld_update_downloads_and_optionally_restarts(monkeypatch):
    server = DummyServer("palalpha")
    server.data["dir"] = "/srv/pal/"
    calls = []

    monkeypatch.setattr(
        palworld.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    palworld.update(server, validate=True, restart=True)

    assert calls == [("/srv/pal/", 2394010, True, True)]
    assert server.start_calls == 1
