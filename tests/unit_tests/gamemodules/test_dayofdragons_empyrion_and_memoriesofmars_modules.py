import gamemodules.dayofdragonsserver as dayofdragonsserver
import gamemodules.empyrionserver as empyrionserver
import gamemodules.memoriesofmarsserver as memoriesofmarsserver


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


def test_dayofdragons_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("dod")
    exe = tmp_path / "DragonsServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "DragonsServer.sh",
                        "port": 7777, "queryport": 27015})

    cmd, cwd = dayofdragonsserver.get_start_command(server)

    assert cmd == ["./DragonsServer.sh", "-Port=7777", "-QueryPort=27015", "-log"]
    assert cwd == server.data["dir"]


def test_empyrion_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(
        empyrionserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: list(cmd),
    )
    server = DummyServer("emp")
    exe = tmp_path / "EmpyrionDedicated.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "EmpyrionDedicated.exe"})

    cmd, cwd = empyrionserver.get_start_command(server)

    assert cmd == ["EmpyrionDedicated.exe"]
    assert cwd == server.data["dir"]


def test_memoriesofmars_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("mom")
    exe = tmp_path / "MemoriesOfMarsServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "MemoriesOfMarsServer.sh",
                        "port": 7777, "queryport": 27015})

    cmd, cwd = memoriesofmarsserver.get_start_command(server)

    assert cmd == ["./MemoriesOfMarsServer.sh", "-Port=7777", "-QueryPort=27015", "-log"]
    assert cwd == server.data["dir"]


def test_three_module_updates_download_and_optionally_restart(monkeypatch):
    dod = DummyServer("dod")
    dod.data["dir"] = "/srv/dod/"
    emp = DummyServer("emp")
    emp.data["dir"] = "/srv/emp/"
    mom = DummyServer("mom")
    mom.data["dir"] = "/srv/mom/"
    calls = []

    monkeypatch.setattr(
        dayofdragonsserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    dayofdragonsserver.update(dod, validate=True, restart=True)
    empyrionserver.update(emp, validate=False, restart=False)
    memoriesofmarsserver.update(mom, validate=False, restart=False)

    assert ("/srv/dod/", 1088320, True, True) in calls
    assert ("/srv/emp/", 530870, True, False) in calls
    assert ("/srv/mom/", 897590, True, False) in calls
    assert dod.start_calls == 1
