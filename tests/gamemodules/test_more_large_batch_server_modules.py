import gamemodules.primalcarnageextinctionserver as primalcarnageextinctionserver
import gamemodules.returntomoriaserver as returntomoriaserver
import gamemodules.saleblazersserver as saleblazersserver
import gamemodules.terratechworldsserver as terratechworldsserver
import gamemodules.theforestserver as theforestserver


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


def test_primalcarnage_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(primalcarnageextinctionserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("pce")
    exe = tmp_path / "PCEdedicated.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "PCEdedicated.exe"})

    cmd, cwd = primalcarnageextinctionserver.get_start_command(server)

    assert cmd == ["PCEdedicated.exe", "server"]
    assert cwd == server.data["dir"]


def test_returntomoria_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(returntomoriaserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("moria")
    exe = tmp_path / "MoriaServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "MoriaServer.exe"})

    cmd, cwd = returntomoriaserver.get_start_command(server)

    assert cmd == ["MoriaServer.exe"]
    assert cwd == server.data["dir"]


def test_saleblazers_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(saleblazersserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("sale")
    exe_dir = tmp_path / "Default"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "Saleblazers.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Default/Saleblazers.exe"})

    cmd, cwd = saleblazersserver.get_start_command(server)

    assert cmd == ["Default/Saleblazers.exe"]
    assert cwd == server.data["dir"]


def test_terratechworlds_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(terratechworldsserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("ttw")
    exe = tmp_path / "TT2Server.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "TT2Server.exe"})

    cmd, cwd = terratechworldsserver.get_start_command(server)

    assert cmd == ["TT2Server.exe", "-log"]
    assert cwd == server.data["dir"]


def test_theforest_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(theforestserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("forest")
    exe = tmp_path / "TheForestDedicatedServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "TheForestDedicatedServer.exe"})

    cmd, cwd = theforestserver.get_start_command(server)

    assert cmd[0] == "TheForestDedicatedServer.exe"
    assert "-nosteamclient" in cmd
    assert cwd == server.data["dir"]


def test_more_large_batch_updates_download_and_optionally_restart(monkeypatch):
    pce = DummyServer("pce")
    pce.data["dir"] = "/srv/pce/"
    moria = DummyServer("moria")
    moria.data["dir"] = "/srv/moria/"
    sale = DummyServer("sale")
    sale.data["dir"] = "/srv/sale/"
    ttw = DummyServer("ttw")
    ttw.data["dir"] = "/srv/ttw/"
    forest = DummyServer("forest")
    forest.data["dir"] = "/srv/forest/"
    calls = []

    monkeypatch.setattr(
        primalcarnageextinctionserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    primalcarnageextinctionserver.update(pce, validate=True, restart=True)
    returntomoriaserver.update(moria, validate=False, restart=False)
    saleblazersserver.update(sale, validate=False, restart=False)
    terratechworldsserver.update(ttw, validate=False, restart=False)
    theforestserver.update(forest, validate=False, restart=False)

    assert ("/srv/pce/", 336400, True, True) in calls
    assert ("/srv/moria/", 3349480, True, False) in calls
    assert ("/srv/sale/", 3099600, True, False) in calls
    assert ("/srv/ttw/", 2533070, True, False) in calls
    assert ("/srv/forest/", 556450, True, False) in calls
    assert pce.start_calls == 1
