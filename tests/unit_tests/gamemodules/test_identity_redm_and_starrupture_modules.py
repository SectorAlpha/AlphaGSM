import gamemodules.redmserver as redmserver
import gamemodules.starruptureserver as starruptureserver


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


def test_redm_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("redm")
    exe = tmp_path / "run.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "run.sh", "port": 30120})
    server_data_dir = tmp_path / "server-data"
    server_data_dir.mkdir()
    (server_data_dir / "server.cfg").write_text("sv_licenseKey test\n")

    cmd, cwd = redmserver.get_start_command(server)

    assert cmd[0] == "./run.sh"
    assert "sv_port" in cmd
    assert cwd == server.data["dir"]


def test_starrupture_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(starruptureserver.proton, "wrap_command", lambda cmd, wineprefix=None, prefer_proton=False: list(cmd))
    server = DummyServer("star")
    exe = tmp_path / "StarRupture" / "Binaries" / "Win64" / "StarRuptureServerEOS-Win64-Shipping.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe",
            "port": 7777,
            "servername": "AlphaGSM StarRupture",
            "maxplayers": 4,
        }
    )

    cmd, cwd = starruptureserver.get_start_command(server)

    assert cmd == [
        "StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe",
        "-Log",
        "-MULTIHOME=0.0.0.0",
        "-Port=7777",
        "-MaxPlayers=4",
        "-ServerName=AlphaGSM StarRupture",
    ]
    assert cwd == server.data["dir"]
