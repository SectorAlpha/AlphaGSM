"""Unit tests for all valve_server-backed game modules missing dedicated coverage.

Each module is a thin wrapper around ``define_valve_server_module`` so the tests
verify that ``configure`` populates expected data-store fields and
``get_start_command`` builds the correct launch command.
"""

from types import SimpleNamespace

import importlib
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_server(name="alpha"):
    return SimpleNamespace(name=name, data={})


def _configure_and_check(module_name, expected_app_id, expected_game_dir,
                         expected_exe, expected_map, tmp_path):
    module = importlib.import_module(f"gamemodules.{module_name}")
    server = _make_server()

    module.configure(server, False, 27015, str(tmp_path))

    assert server.data["Steam_AppID"] == expected_app_id
    assert server.data["game_dir"] == expected_game_dir
    assert server.data["exe_name"] == expected_exe
    assert server.data["startmap"] == expected_map
    assert server.data["port"] == 27015
    return module, server


def _start_command_check(module, server, tmp_path, exe_name):
    exe = tmp_path / exe_name
    exe.write_text("")

    cmd, cwd = module.get_start_command(server)

    assert cmd[0] == f"./{exe_name}"
    assert cwd == server.data["dir"]
    return cmd


# ── Garry's Mod ──────────────────────────────────────────────────────────────

def test_gmodserver_configure(tmp_path):
    mod, _ = _configure_and_check(
        "gmodserver", 4020, "garrysmod", "srcds_run", "gm_construct", tmp_path
    )


def test_gmodserver_start_command(tmp_path):
    mod, server = _configure_and_check(
        "gmodserver", 4020, "garrysmod", "srcds_run", "gm_construct", tmp_path
    )
    cmd = _start_command_check(mod, server, tmp_path, "srcds_run")
    assert "-game" in cmd and "garrysmod" in cmd


# ── Counter-Strike: Source ───────────────────────────────────────────────────

def test_cssserver_configure(tmp_path):
    _configure_and_check("cssserver", 232330, "cstrike", "srcds_run", "de_dust2", tmp_path)


def test_cssserver_start_command(tmp_path):
    mod, server = _configure_and_check(
        "cssserver", 232330, "cstrike", "srcds_run", "de_dust2", tmp_path
    )
    cmd = _start_command_check(mod, server, tmp_path, "srcds_run")
    assert "cstrike" in cmd


# ── Left 4 Dead 2 ───────────────────────────────────────────────────────────

def test_l4d2server_configure(tmp_path):
    _configure_and_check(
        "l4d2server", 222860, "left4dead2", "srcds_run", "c5m1_waterfront", tmp_path
    )


def test_l4d2server_start_command(tmp_path):
    mod, server = _configure_and_check(
        "l4d2server", 222860, "left4dead2", "srcds_run", "c5m1_waterfront", tmp_path
    )
    cmd = _start_command_check(mod, server, tmp_path, "srcds_run")
    assert "left4dead2" in cmd


# ── Left 4 Dead ──────────────────────────────────────────────────────────────

def test_l4dserver_configure(tmp_path):
    _configure_and_check(
        "l4dserver", 222840, "left4dead", "srcds_run", "l4d_hospital01_apartment", tmp_path
    )


# ── Half-Life 2: Deathmatch ─────────────────────────────────────────────────

def test_hl2dmserver_configure(tmp_path):
    _configure_and_check(
        "hl2dmserver", 232370, "hl2mp", "srcds_run", "dm_lockdown", tmp_path
    )


# ── Half-Life: Deathmatch (GoldSrc) ─────────────────────────────────────────

def test_hldmserver_configure(tmp_path):
    _configure_and_check("hldmserver", 90, "valve", "hlds_run", "crossfire", tmp_path)


# ── Half-Life Deathmatch: Source ─────────────────────────────────────────────

def test_hldmsserver_configure(tmp_path):
    _configure_and_check("hldmsserver", 255470, "hl1mp", "srcds_run", "crossfire", tmp_path)


# ── Insurgency ───────────────────────────────────────────────────────────────

def test_insserver_configure(tmp_path):
    _configure_and_check(
        "insserver", 237410, "insurgency", "srcds_run", "embassy_coop checkpoint", tmp_path
    )


# ── Day of Infamy ────────────────────────────────────────────────────────────

def test_doiserver_configure(tmp_path):
    _configure_and_check(
        "doiserver", 462310, "doi", "srcds_run", "bastogne stronghold", tmp_path
    )


# ── Day of Defeat: Source ────────────────────────────────────────────────────

def test_dodsserver_configure(tmp_path):
    _configure_and_check("dodsserver", 232290, "dod", "srcds_run", "dod_Anzio", tmp_path)


# ── Day of Defeat (GoldSrc) ─────────────────────────────────────────────────

def test_dodserver_configure(tmp_path):
    _configure_and_check("dodserver", 90, "dod", "hlds_run", "dod_Anzio", tmp_path)


# ── Fistful of Frags ────────────────────────────────────────────────────────

def test_fofserver_configure(tmp_path):
    _configure_and_check("fofserver", 295230, "fof", "srcds_run", "fof_depot", tmp_path)


# ── Double Action: Boogaloo ──────────────────────────────────────────────────

def test_dabserver_configure(tmp_path):
    _configure_and_check("dabserver", 317800, "dab", "dabds.sh", "da_rooftops", tmp_path)


# ── Deathmatch Classic ───────────────────────────────────────────────────────

def test_dmcserver_configure(tmp_path):
    _configure_and_check("dmcserver", 90, "dmc", "hlds_run", "dcdm5", tmp_path)


# ── BrainBread 2 ─────────────────────────────────────────────────────────────

def test_bb2server_configure(tmp_path):
    _configure_and_check(
        "bb2server", 475370, "brainbread2", "srcds_run", "bba_barracks", tmp_path
    )


# ── BrainBread (GoldSrc) ─────────────────────────────────────────────────────

def test_bbserver_configure(tmp_path):
    _configure_and_check(
        "bbserver", 90, "brainbread", "hlds_run", "bb_chp4_slaywatch", tmp_path
    )


# ── Blade Symphony ───────────────────────────────────────────────────────────

def test_bsserver_configure(tmp_path):
    _configure_and_check(
        "bsserver", 228780, "berimbau", "bin/srcds_run.sh", "duel_winter", tmp_path
    )


# ── Black Mesa: Deathmatch ───────────────────────────────────────────────────

def test_bmdmserver_configure(tmp_path):
    _configure_and_check("bmdmserver", 346680, "bms", "srcds_run", "dm_bounce", tmp_path)


# ── Codename CURE ────────────────────────────────────────────────────────────

def test_ccserver_configure(tmp_path):
    _configure_and_check("ccserver", 383410, "cure", "srcds_run", "cbe_bunker", tmp_path)


# ── Counter-Strike: Condition Zero ───────────────────────────────────────────

def test_csczserver_configure(tmp_path):
    _configure_and_check("csczserver", 90, "czero", "hlds_run", "de_dust2", tmp_path)


# ── Counter-Strike (GoldSrc) ─────────────────────────────────────────────────

def test_csserver_configure(tmp_path):
    _configure_and_check("csserver", 90, "cstrike", "hlds_run", "de_dust2", tmp_path)


# ── Dystopia ─────────────────────────────────────────────────────────────────

def test_dysserver_configure(tmp_path):
    _configure_and_check(
        "dysserver", 17585, "dystopia", "bin/srcds_run.sh", "dys_broadcast", tmp_path
    )


# ── Empires Mod ──────────────────────────────────────────────────────────────

def test_emserver_configure(tmp_path):
    _configure_and_check(
        "emserver", 460040, "empires", "srcds_run", "con_district402", tmp_path
    )


# ── SourceForts Classic ──────────────────────────────────────────────────────

def test_sfcserver_configure(tmp_path):
    _configure_and_check(
        "sfcserver", 244310, "sfclassic", "srcds_run", "sf_astrodome", tmp_path
    )


# ── Nuclear Dawn ─────────────────────────────────────────────────────────────

def test_ndserver_configure(tmp_path):
    _configure_and_check("ndserver", 111710, "nucleardawn", "srcds_run", "hydro", tmp_path)


# ── Natural Selection (GoldSrc) ──────────────────────────────────────────────

def test_nsserver_configure(tmp_path):
    _configure_and_check("nsserver", 90, "ns", "hlds_run", "ns_hera", tmp_path)


# ── No More Room in Hell ─────────────────────────────────────────────────────

def test_nmrihserver_configure(tmp_path):
    _configure_and_check(
        "nmrihserver", 317670, "nmrih", "srcds_run", "nmo_broadway", tmp_path
    )


# ── Opposing Force ───────────────────────────────────────────────────────────

def test_opforserver_configure(tmp_path):
    _configure_and_check("opforserver", 90, "gearbox", "hlds_run", "op4_bootcamp", tmp_path)


# ── Pirates, Vikings & Knights II ────────────────────────────────────────────

def test_pvkiiserver_configure(tmp_path):
    _configure_and_check("pvkiiserver", 17575, "pvkii", "srcds_run", "bt_island", tmp_path)


# ── Ricochet ─────────────────────────────────────────────────────────────────

def test_ricochetserver_configure(tmp_path):
    _configure_and_check(
        "ricochetserver", 90, "ricochet", "hlds_run", "rc_arena", tmp_path
    )


# ── Sven Co-op ───────────────────────────────────────────────────────────────

def test_svenserver_configure(tmp_path):
    _configure_and_check(
        "svenserver", 276060, "svencoop", "svends_run", "svencoop1", tmp_path
    )


# ── Team Fortress Classic ────────────────────────────────────────────────────

def test_tfcserver_configure(tmp_path):
    _configure_and_check("tfcserver", 90, "tfc", "hlds_run", "dustbowl", tmp_path)


# ── The Specialists ──────────────────────────────────────────────────────────

def test_tsserver_configure(tmp_path):
    _configure_and_check("tsserver", 90, "ts", "hlds_run", "ts_neobaroque", tmp_path)


# ── Zombie Master: Reborn ────────────────────────────────────────────────────

def test_zmrserver_configure(tmp_path):
    _configure_and_check(
        "zmrserver", 244310, "zombie_master_reborn", "srcds_run", "zm_docksofthedead", tmp_path
    )


# ── Zombie Panic! Source ─────────────────────────────────────────────────────

def test_zpsserver_configure(tmp_path):
    _configure_and_check("zpsserver", 17505, "zps", "srcds_run", "zps_deadend", tmp_path)


# ── IOSoccer ─────────────────────────────────────────────────────────────────

def test_iosserver_configure(tmp_path):
    _configure_and_check("iosserver", 673990, "iosoccer", "srcds_run", "8v8_vienna", tmp_path)


# ── Action: Source ───────────────────────────────────────────────────────────

def test_ahl2server_configure(tmp_path):
    _configure_and_check("ahl2server", 985050, "ahl2", "srcds_run", "act_airport", tmp_path)


# ── Action Half-Life (GoldSrc) ───────────────────────────────────────────────

def test_ahlserver_configure(tmp_path):
    _configure_and_check("ahlserver", 90, "action", "hlds_run", "ahl_hydro", tmp_path)


# ── Base Defense ─────────────────────────────────────────────────────────────

def test_bdserver_configure(tmp_path):
    _configure_and_check("bdserver", 817300, "bdef", "hlds_run", "pve_tomb", tmp_path)


# ── Vampire Slayer ───────────────────────────────────────────────────────────

def test_vsserver_configure(tmp_path):
    _configure_and_check("vsserver", 90, "vs", "hlds_run", "vs_frost", tmp_path)
