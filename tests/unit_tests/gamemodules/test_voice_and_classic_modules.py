import gamemodules.mumbleserver as mumbleserver
import gamemodules.qlserver as qlserver
import gamemodules.ut2k4server as ut2k4server
import gamemodules.ut99server as ut99server


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


def test_qlserver_configure_sets_defaults(tmp_path):
    server = DummyServer("qlalpha")

    qlserver.configure(server, ask=False, port=27960, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 349090
    assert server.data["hostname"] == "AlphaGSM qlalpha"
    assert server.data["servercfg"] == "baseq3/server.cfg"


def test_qlserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("qlalpha")
    exe = tmp_path / "qzeroded.x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "qzeroded.x64",
            "port": 27960,
            "hostname": "AlphaGSM qlalpha",
            "servercfg": "baseq3/server.cfg",
            "startmap": "campgrounds",
        }
    )

    cmd, cwd = qlserver.get_start_command(server)

    assert cmd[0] == "./qzeroded.x64"
    assert "net_port" in cmd
    assert "sv_hostname" in cmd
    assert cwd == server.data["dir"]


def test_qlserver_runtime_requirements_use_steamcmd_linux_family(tmp_path):
    (tmp_path / "qzeroded.x64").write_text("")
    server = DummyServer("qlalpha")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "qzeroded.x64",
            "port": 27960,
            "hostname": "AlphaGSM qlalpha",
            "servercfg": "baseq3/server.cfg",
            "startmap": "campgrounds",
        }
    )

    requirements = qlserver.get_runtime_requirements(server)
    spec = qlserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27960, "container": 27960, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][3] == "/srv/server"


def test_qlserver_update_downloads_and_optionally_restarts(monkeypatch):
    server = DummyServer("qlalpha")
    server.data["dir"] = "/srv/ql/"
    calls = []

    monkeypatch.setattr(
        qlserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    qlserver.update(server, validate=True, restart=True)

    assert calls == [("/srv/ql/", 349090, True, True)]
    assert server.start_calls == 1


def test_mumbleserver_install_writes_default_config(tmp_path):
    server = DummyServer("mumblealpha")
    mumbleserver.configure(server, ask=False, port=64738, dir=str(tmp_path), exe_name="murmurd")

    mumbleserver.install(server)

    config_path = tmp_path / "mumble-server.ini"
    assert config_path.exists()
    assert "port=64738" in config_path.read_text()


def test_mumbleserver_get_start_command_uses_ini_file(tmp_path):
    server = DummyServer("mumblealpha")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "murmurd", "port": 64738})

    cmd, cwd = mumbleserver.get_start_command(server)

    assert cmd == ["murmurd", "-fg", "-ini", str(tmp_path / "mumble-server.ini")]
    assert cwd == server.data["dir"]


def test_mumbleserver_runtime_requirements_use_simple_tcp_family(tmp_path):
    server = DummyServer("mumblealpha")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "murmurd", "port": 64738})

    requirements = mumbleserver.get_runtime_requirements(server)
    spec = mumbleserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "simple-tcp"
    assert requirements["ports"] == [
        {"host": 64738, "container": 64738, "protocol": "tcp"},
        {"host": 64738, "container": 64738, "protocol": "udp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"] == ["murmurd", "-fg", "-ini", "/srv/server/mumble-server.ini"]


def test_ut99server_install_extracts_archive(tmp_path, monkeypatch):
    server = DummyServer("ut99alpha")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "System/ucc-bin",
            "url": "http://example.com/ut99.tar.gz",
            "download_name": "ut99.tar.gz",
        }
    )
    download_root = tmp_path / "download"
    extracted = download_root / "ut99"
    binary = extracted / "System" / "ucc-bin"
    binary.parent.mkdir(parents=True)
    binary.write_text("")

    monkeypatch.setattr(ut99server, "install_archive", lambda server_obj, compression: [
        __import__("utils.archive_install").archive_install.sync_tree(str(extracted), server_obj.data["dir"]),
        server_obj.data.__setitem__("current_url", server_obj.data["url"]),
        server_obj.data.save(),
    ])

    ut99server.install(server)

    assert (tmp_path / "System" / "ucc-bin").exists()
    assert server.data["current_url"] == "http://example.com/ut99.tar.gz"


def test_ut99server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ut99alpha")
    exe = tmp_path / "System" / "ucc-bin"
    exe.parent.mkdir()
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "System/ucc-bin",
            "port": 7777,
            "startmap": "DM-Deck16][",
            "gametype": "Botpack.DeathMatchPlus",
            "maxplayers": "16",
            "configfile": "System/UnrealTournament.ini",
        }
    )

    cmd, cwd = ut99server.get_start_command(server)

    assert cmd[0] == "./System/ucc-bin"
    assert "-port=7777" in cmd
    assert cwd == server.data["dir"]


def test_ut2k4server_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("ut2k4alpha")

    ut2k4server.configure(
        server,
        ask=False,
        port=7777,
        dir=str(tmp_path),
        url="http://example.com/ut2004.tar.gz",
    )

    assert server.data["startmap"] == "DM-Antalus"
    assert server.data["gametype"] == "XGame.xDeathMatch"
    assert server.data["download_name"] == "ut2004.tar.gz"


def test_ut2k4server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ut2k4alpha")
    exe = tmp_path / "System" / "ucc-bin"
    exe.parent.mkdir()
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "System/ucc-bin",
            "port": 7777,
            "startmap": "DM-Antalus",
            "gametype": "XGame.xDeathMatch",
            "maxplayers": "16",
            "configfile": "System/UT2004.ini",
        }
    )

    cmd, cwd = ut2k4server.get_start_command(server)

    assert cmd[0] == "./System/ucc-bin"
    assert "DM-Antalus?Game=XGame.xDeathMatch?MaxPlayers=16" in cmd
    assert cwd == server.data["dir"]
