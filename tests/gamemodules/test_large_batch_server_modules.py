import gamemodules.battlecryoffreedomserver as battlecryoffreedomserver
import gamemodules.deadmatterserver as deadmatterserver
import gamemodules.lifeisfeudalserver as lifeisfeudalserver
import gamemodules.medievalengineersserver as medievalengineersserver
import gamemodules.sonsoftheforestserver as sonsoftheforestserver


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


def test_battlecryoffreedom_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bcof")
    exe = tmp_path / "BCoF.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "BCoF.exe"})

    cmd, cwd = battlecryoffreedomserver.get_start_command(server)

    assert cmd[0] == "./BCoF.exe"
    assert "-server" in cmd
    assert cwd == server.data["dir"]


def test_deadmatter_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("deadmatter")
    exe = tmp_path / "DeadMatterServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "DeadMatterServer.sh"})

    cmd, cwd = deadmatterserver.get_start_command(server)

    assert cmd == ["./DeadMatterServer.sh", "-log"]
    assert cwd == server.data["dir"]


def test_lifeisfeudal_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("lif")
    exe = tmp_path / "ddctd_cm_yo_server.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "ddctd_cm_yo_server.exe"})

    cmd, cwd = lifeisfeudalserver.get_start_command(server)

    assert cmd == ["./ddctd_cm_yo_server.exe"]
    assert cwd == server.data["dir"]


def test_medievalengineers_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("me")
    exe_dir = tmp_path / "DedicatedServer64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "MedievalEngineersDedicated.exe"
    exe.write_text("")
    server.data.update(
        {"dir": str(tmp_path) + "/", "exe_name": "DedicatedServer64/MedievalEngineersDedicated.exe", "port": 27016}
    )

    cmd, cwd = medievalengineersserver.get_start_command(server)

    assert cmd[0] == "./DedicatedServer64/MedievalEngineersDedicated.exe"
    assert "console" in cmd
    assert cwd == server.data["dir"]


def test_sonsoftheforest_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("sotf")
    exe = tmp_path / "SonsOfTheForestDS.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "SonsOfTheForestDS.exe"})

    cmd, cwd = sonsoftheforestserver.get_start_command(server)

    assert cmd[0] == "./SonsOfTheForestDS.exe"
    assert "-log" in cmd
    assert cwd == server.data["dir"]


def test_large_batch_updates_download_and_optionally_restart(monkeypatch):
    bcof = DummyServer("bcof")
    bcof.data["dir"] = "/srv/bcof/"
    dead = DummyServer("dead")
    dead.data["dir"] = "/srv/dead/"
    lif = DummyServer("lif")
    lif.data["dir"] = "/srv/lif/"
    me = DummyServer("me")
    me.data["dir"] = "/srv/me/"
    sotf = DummyServer("sotf")
    sotf.data["dir"] = "/srv/sotf/"
    calls = []

    monkeypatch.setattr(
        battlecryoffreedomserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    battlecryoffreedomserver.update(bcof, validate=True, restart=True)
    deadmatterserver.update(dead, validate=False, restart=False)
    lifeisfeudalserver.update(lif, validate=False, restart=False)
    medievalengineersserver.update(me, validate=False, restart=False)
    sonsoftheforestserver.update(sotf, validate=False, restart=False)

    assert ("/srv/bcof/", 1362540, True, True) in calls
    assert ("/srv/dead/", 1110990, True, False) in calls
    assert ("/srv/lif/", 320850, True, False) in calls
    assert ("/srv/me/", 367970, True, False) in calls
    assert ("/srv/sotf/", 2465200, True, False) in calls
    assert bcof.start_calls == 1
