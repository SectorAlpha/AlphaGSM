import gamemodules.ecoserver as ecoserver
import gamemodules.twserver as twserver
import gamemodules.wfserver as wfserver


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


def test_twserver_configure_sets_defaults(tmp_path):
    server = DummyServer("tw")

    twserver.configure(server, ask=False, port=8303, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 380840
    assert server.data["configfile"] == "autoexec.cfg"


def test_wfserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("wf")
    exe = tmp_path / "wf_server.x86_64"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "wf_server.x86_64", "fs_game": "basewf", "hostname": "AlphaGSM wf", "port": 44400, "startmap": "wfa1"})

    cmd, cwd = wfserver.get_start_command(server)

    assert cmd[0] == "./wf_server.x86_64"
    assert "net_port" in cmd
    assert cwd == server.data["dir"]


def test_wfserver_runtime_requirements_use_steamcmd_linux_family(tmp_path):
    (tmp_path / "wf_server.x86_64").write_text("")
    server = DummyServer("wf")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "wf_server.x86_64",
            "fs_game": "basewf",
            "hostname": "AlphaGSM wf",
            "port": 44400,
            "startmap": "wfa1",
        }
    )

    requirements = wfserver.get_runtime_requirements(server)
    spec = wfserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 44400, "container": 44400, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./wf_server.x86_64"


def test_ecoserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("eco")
    exe = tmp_path / "EcoServer"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "EcoServer", "port": 3000, "world": "eco", "storage": "Storage"})

    cmd, cwd = ecoserver.get_start_command(server)

    assert cmd == ["./EcoServer", "-nogui", "-port", "3000", "-world", "eco", "-storedirectory", "Storage"]
    assert cwd == server.data["dir"]


def test_tail_modules_update_downloads_and_optionally_restart(monkeypatch):
    tw = DummyServer("tw")
    tw.data["dir"] = "/srv/tw/"
    wf = DummyServer("wf")
    wf.data["dir"] = "/srv/wf/"
    eco = DummyServer("eco")
    eco.data["dir"] = "/srv/eco/"
    calls = []

    monkeypatch.setattr(
        twserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    twserver.update(tw, validate=True, restart=True)
    wfserver.update(wf, validate=False, restart=False)
    ecoserver.update(eco, validate=False, restart=False)

    assert ("/srv/tw/", 380840, False, True) in calls
    assert ("/srv/wf/", 1136510, True, False) in calls
    assert ("/srv/eco/", 739590, True, False) in calls
    assert tw.start_calls == 1
