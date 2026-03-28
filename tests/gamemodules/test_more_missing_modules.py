import gamemodules.arksurvivalascended as arksurvivalascended
import gamemodules.conanexiles as conanexiles
import gamemodules.nightingale as nightingale


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


def test_conanexiles_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("conan")
    exe_dir = tmp_path / "ConanSandbox" / "Binaries" / "Linux"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "ConanSandboxServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ConanSandbox/Binaries/Linux/ConanSandboxServer",
            "map": "ConanSandbox",
            "maxplayers": 40,
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = conanexiles.get_start_command(server)

    assert cmd[0] == "./ConanSandbox/Binaries/Linux/ConanSandboxServer"
    assert "-Port=7777" in cmd
    assert cwd == server.data["dir"]


def test_arksurvivalascended_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(arksurvivalascended.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("asa")
    exe_dir = tmp_path / "ShooterGame" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "ArkAscendedServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ShooterGame/Binaries/Win64/ArkAscendedServer.exe",
            "map": "TheIsland_WP",
            "sessionname": "AlphaGSM asa",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 70,
            "adminpassword": "alphagsm",
            "serverpassword": "",
        }
    )

    cmd, cwd = arksurvivalascended.get_start_command(server)

    assert cmd[0] == "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    assert "-server" in cmd
    assert cwd == server.data["dir"]


def test_nightingale_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("night")
    exe = tmp_path / "NWXServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "NWXServer.sh"})

    cmd, cwd = nightingale.get_start_command(server)

    assert cmd == ["./NWXServer.sh"]
    assert cwd == server.data["dir"]


def test_more_missing_modules_update_downloads_and_optionally_restart(monkeypatch):
    conan = DummyServer("conan")
    conan.data["dir"] = "/srv/conan/"
    asa = DummyServer("asa")
    asa.data["dir"] = "/srv/asa/"
    night = DummyServer("night")
    night.data["dir"] = "/srv/night/"
    calls = []

    monkeypatch.setattr(
        conanexiles.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    conanexiles.update(conan, validate=True, restart=True)
    arksurvivalascended.update(asa, validate=False, restart=False)
    nightingale.update(night, validate=False, restart=False)

    assert ("/srv/conan/", 443030, True, True) in calls
    assert ("/srv/asa/", 2430930, True, False) in calls
    assert ("/srv/night/", 3796810, True, False) in calls
    assert conan.start_calls == 1
