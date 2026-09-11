import gamemodules.bf1942server as bf1942server
import gamemodules.bfvserver as bfvserver
import gamemodules.cod2server as cod2server
import gamemodules.cod4server as cod4server
import gamemodules.codserver as codserver
import gamemodules.coduoserver as coduoserver
import gamemodules.codwawserver as codwawserver


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


def test_codserver_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("cod")

    codserver.configure(server, ask=False, port=28960, dir=str(tmp_path), url="http://example.com/cod.tar.gz")

    assert server.data["moddir"] == "main"
    assert server.data["startmap"] == "mp_carentan"


def test_cod2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("cod2")
    exe = tmp_path / "cod2_lnxded"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "cod2_lnxded",
            "moddir": "main",
            "hostname": "AlphaGSM cod2",
            "port": 28960,
            "startmap": "mp_toujane",
        }
    )

    cmd, cwd = cod2server.get_start_command(server)

    assert cmd[0] == "./cod2_lnxded"
    assert "+map" in cmd
    assert "fs_game" not in cmd
    assert cwd == server.data["dir"]


def test_cod4server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("cod4")
    exe = tmp_path / "cod4_lnxded"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "cod4_lnxded",
            "moddir": "main",
            "hostname": "AlphaGSM cod4",
            "port": 28960,
            "startmap": "mp_crash",
        }
    )

    cmd, cwd = cod4server.get_start_command(server)

    assert cmd[0] == "./cod4_lnxded"
    assert "sv_hostname" in cmd
    assert "fs_game" not in cmd
    assert cwd == server.data["dir"]


def test_cod4server_get_start_command_keeps_fs_game_for_custom_moddir(tmp_path):
    server = DummyServer("cod4mod")
    exe = tmp_path / "cod4_lnxded"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "cod4_lnxded",
            "moddir": "promodlive",
            "hostname": "AlphaGSM cod4mod",
            "port": 28960,
            "startmap": "mp_crash",
        }
    )

    cmd, _ = cod4server.get_start_command(server)

    assert "fs_game" in cmd
    assert "promodlive" in cmd


def test_coduoserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("coduo")
    exe = tmp_path / "coduo_lnxded"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "coduo_lnxded",
            "moddir": "uo",
            "hostname": "AlphaGSM coduo",
            "port": 28960,
            "startmap": "mp_brecourt",
        }
    )

    cmd, cwd = coduoserver.get_start_command(server)

    assert cmd[0] == "./coduo_lnxded"
    assert "+set" in cmd
    assert "fs_game" not in cmd
    assert cwd == server.data["dir"]


def test_codwaw_and_battlefield_commands_build_expected_args(tmp_path):
    waw = DummyServer("waw")
    wawexe = tmp_path / "codwaw_lnxded"
    wawexe.write_text("")
    waw.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "codwaw_lnxded",
            "moddir": "main",
            "hostname": "AlphaGSM waw",
            "port": 28960,
            "startmap": "mp_airfield",
        }
    )
    bf = DummyServer("bf")
    bfexe = tmp_path / "bf1942_lnxded"
    bfexe.write_text("")
    bf.data.update({"dir": str(tmp_path) + "/", "exe_name": "bf1942_lnxded", "port": 14567, "startmap": "wake"})
    bfv = DummyServer("bfv")
    bfvexe = tmp_path / "bfvietnam_lnxded"
    bfvexe.write_text("")
    bfv.data.update(
        {"dir": str(tmp_path) + "/", "exe_name": "bfvietnam_lnxded", "port": 15567, "startmap": "operation_hastings"}
    )

    waw_cmd, _ = codwawserver.get_start_command(waw)
    bf_cmd, _ = bf1942server.get_start_command(bf)
    bfv_cmd, _ = bfvserver.get_start_command(bfv)

    assert waw_cmd[0] == "./codwaw_lnxded"
    assert "fs_game" not in waw_cmd
    assert bf_cmd == ["./bf1942_lnxded", "+statusMonitor", "1", "+map", "wake", "+port", "14567"]
    assert bfv_cmd == ["./bfvietnam_lnxded", "+statusMonitor", "1", "+map", "operation_hastings", "+port", "15567"]


def test_cod_family_query_and_info_use_declared_protocol():
    for module in (cod2server, cod4server, codserver, coduoserver, codwawserver):
        server = DummyServer(module.__name__)
        server.data["port"] = 28960

        query_address = module.get_query_address(server)
        info_address = module.get_info_address(server)

        assert query_address[1] == 28960
        assert query_address[2] == ("quake" if module is codwawserver else "tcp")
        assert info_address == query_address
