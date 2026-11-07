import gamemodules.arma2coserver as arma2coserver
import gamemodules.arma3altislifeserver as arma3altislifeserver
import gamemodules.arma3desolationreduxserver as arma3desolationreduxserver
import pytest
from server.settable_keys import resolve_requested_key


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


def test_arma2coserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("arma2")
    exe = tmp_path / "arma2oaserver"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma2oaserver",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "empty",
            "mod": "",
        }
    )

    cmd, cwd = arma2coserver.get_start_command(server)

    assert cmd[0] == "./arma2oaserver"
    assert "-port=2302" in cmd
    assert cwd == server.data["dir"]


def test_arma3altislifeserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("altis")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "Altis",
            "mod": "",
            "mission": "Altis_Life.Altis",
        }
    )

    cmd, cwd = arma3altislifeserver.get_start_command(server)

    assert "-mission=Altis_Life.Altis" in cmd
    assert "-world=Altis" in cmd
    assert cwd == server.data["dir"]


def test_arma3desolationreduxserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("deso")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "chernarus_summer",
            "mod": "@DesolationRedux",
            "servermod": "",
            "mission": "desolationRedux.chernarus_summer",
        }
    )

    cmd, cwd = arma3desolationreduxserver.get_start_command(server)

    assert "-mod=@DesolationRedux" in cmd
    assert "-mission=desolationRedux.chernarus_summer" in cmd
    assert cwd == server.data["dir"]


def test_more_arma_variant_modules_update_downloads_and_optional_restart(monkeypatch):
    arma2 = DummyServer("arma2")
    arma2.data["dir"] = "/srv/arma2/"
    altis = DummyServer("altis")
    altis.data["dir"] = "/srv/altis/"
    deso = DummyServer("deso")
    deso.data["dir"] = "/srv/deso/"
    calls = []

    monkeypatch.setattr(
        arma2coserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    arma2coserver.update(arma2, validate=True, restart=True)
    arma3altislifeserver.update(altis, validate=False, restart=False)
    arma3desolationreduxserver.update(deso, validate=False, restart=False)

    assert ("/srv/arma2/", 33935, True, True) in calls
    assert ("/srv/altis/", 233780, True, False) in calls
    assert ("/srv/deso/", 233780, True, False) in calls
    assert arma2.start_calls == 1


@pytest.mark.parametrize(
    "module",
    (arma2coserver, arma3altislifeserver, arma3desolationreduxserver),
)
def test_more_arma_variants_expose_servername_setting_schema(module):
    resolved = resolve_requested_key("hostname", module.setting_schema)

    assert resolved.canonical_key == "servername"


@pytest.mark.parametrize(
    "module",
    (arma2coserver, arma3altislifeserver, arma3desolationreduxserver),
)
def test_more_arma_variants_sync_server_config_writes_hostname(tmp_path, module):
    server = DummyServer("variant")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "configfile": "server.cfg",
            "servername": "Alpha Variant",
        }
    )

    module.sync_server_config(server)

    assert (tmp_path / "server.cfg").read_text() == 'hostname = "Alpha Variant";\n'
