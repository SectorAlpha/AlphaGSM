import gamemodules.ckserver as ckserver
import gamemodules.dstserver as dstserver
import gamemodules.jc2server as jc2server


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


def test_dstserver_configure_sets_defaults(tmp_path):
    server = DummyServer("dst")

    dstserver.configure(server, ask=False, port=10999, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 343050
    assert server.data["cluster"] == "dst"


def test_ckserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ck")
    exe = tmp_path / "CoreKeeperServer"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "CoreKeeperServer", "world": "ck", "port": 27015, "maxplayers": "8"})

    cmd, cwd = ckserver.get_start_command(server)

    assert cmd == ["./CoreKeeperServer", "-world", "ck", "-port", "27015", "-maxplayers", "8"]
    assert cwd == server.data["dir"]


def test_jc2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("jc2")
    exe = tmp_path / "openjc2-server"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "openjc2-server", "port": 7777, "maxplayers": "64", "gamemode": "freeroam"})

    cmd, cwd = jc2server.get_start_command(server)

    assert cmd == ["./openjc2-server", "--port", "7777", "--players", "64", "--mode", "freeroam"]
    assert cwd == server.data["dir"]


def test_new_batch_update_downloads_and_optionally_restart(monkeypatch):
    dst = DummyServer("dst")
    dst.data["dir"] = "/srv/dst/"
    ck = DummyServer("ck")
    ck.data["dir"] = "/srv/ck/"
    jc2 = DummyServer("jc2")
    jc2.data["dir"] = "/srv/jc2/"
    calls = []

    monkeypatch.setattr(
        dstserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    dstserver.update(dst, validate=True, restart=True)
    ckserver.update(ck, validate=False, restart=False)
    jc2server.update(jc2, validate=False, restart=False)

    assert ("/srv/dst/", 343050, True, True) in calls
    assert ("/srv/ck/", 1963720, True, False) in calls
    assert ("/srv/jc2/", 261140, True, False) in calls
    assert dst.start_calls == 1
