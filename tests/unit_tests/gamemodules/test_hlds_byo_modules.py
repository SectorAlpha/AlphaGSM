"""Focused BYO coverage for HLDS mod modules missing SteamCMD content."""

from pathlib import Path

import pytest

from server import ServerError
import utils.valve_server as valve_server

import gamemodules.ahlserver as ahlserver
import gamemodules.bbserver as bbserver
import gamemodules.nsserver as nsserver
import gamemodules.tsserver as tsserver
import gamemodules.vsserver as vsserver


class DummyData(dict):
    def save(self):
        return None


class DummyServer:
    def __init__(self, name="alpha"):
        self.name = name
        self.data = DummyData()


@pytest.mark.parametrize(
    ("module", "server_name", "game_dir", "default_map"),
    (
        (ahlserver, "ahl", "action", "ahl_hydro"),
        (bbserver, "bb", "brainbread", "bb_chp4_slaywatch"),
        (nsserver, "ns", "ns", "ns_hera"),
        (tsserver, "ts", "ts", "ts_neobaroque"),
        (vsserver, "vs", "vs", "vs_frost"),
    ),
)
def test_hlds_mod_install_requires_staged_byo_content(
    tmp_path, monkeypatch, module, server_name, game_dir, default_map
):
    monkeypatch.setattr(valve_server.steamcmd, "download", lambda *args, **kwargs: None)
    server = DummyServer(server_name)
    module.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\)"):
        module.install(server)


@pytest.mark.parametrize(
    ("module", "server_name", "game_dir", "default_map"),
    (
        (ahlserver, "ahl", "action", "ahl_hydro"),
        (bbserver, "bb", "brainbread", "bb_chp4_slaywatch"),
        (nsserver, "ns", "ns", "ns_hera"),
        (tsserver, "ts", "ts", "ts_neobaroque"),
        (vsserver, "vs", "vs", "vs_frost"),
    ),
)
def test_hlds_mod_start_requires_staged_byo_content(
    tmp_path, module, server_name, game_dir, default_map
):
    server = DummyServer(server_name)
    module.configure(server, ask=False, port=27015, dir=str(tmp_path))
    (tmp_path / "hlds_run").write_text("")

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\)"):
        module.get_start_command(server)
