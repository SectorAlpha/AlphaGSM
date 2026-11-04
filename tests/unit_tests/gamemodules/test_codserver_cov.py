"""Full coverage tests for codserver."""

import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.codserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.codserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28960, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip")
    assert server.data['port'] == 28960

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 28960
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["28961", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod_lnxded"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.install(server)


def test_stage_gcc3_runtime_copies_extracted_cache_directory(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    (install / "cod_lnxded").write_bytes(b"elf")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "libstdc++.so.5.0.3").write_bytes(b"realstd")
    (cache / "libstdc++.so.5").symlink_to("libstdc++.so.5.0.3")
    (cache / "libgcc_s.so.1").write_bytes(b"gcc")
    (cache / "cod-gcc3-libs.tar.bz2").write_bytes(b"not-a-tar")
    calls = []
    monkeypatch.setattr(mod.downloader, "getpath", lambda *args: calls.append(args) or str(cache))

    def reject_archive(*_args, **_kwargs):
        raise AssertionError("extracted cache must not be opened as a tarball")

    monkeypatch.setattr(mod.tarfile, "open", reject_archive)
    server = DummyServer()
    server.data["dir"] = str(install) + "/"
    server.data["exe_name"] = "cod_lnxded"

    mod._stage_gcc3_runtime(server)

    assert (install / "libstdc++.so.5").read_bytes() == b"realstd"
    assert not (install / "libstdc++.so.5").is_symlink()
    assert (install / "libgcc_s.so.1").read_bytes() == b"gcc"
    assert calls == [("url", (mod.COD_GCC3_LIBS_URL, mod.COD_GCC3_LIBS_NAME, "tar.bz2"))]

    mod._stage_gcc3_runtime(server)
    assert len(calls) == 1


def test_stage_gcc3_runtime_reads_a_tarball_path(tmp_path, monkeypatch):
    import io
    import tarfile

    install = tmp_path / "install"
    install.mkdir()
    (install / "cod_lnxded").write_bytes(b"elf")
    archive_path = tmp_path / "libs.tar.bz2"
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as archive:
        for name, content in (("libstdc++.so.5", b"std"), ("libgcc_s.so.1", b"gcc")):
            data = content
            info = tarfile.TarInfo(name="gcc3/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    archive_path.write_bytes(payload.getvalue())
    monkeypatch.setattr(mod.downloader, "getpath", lambda *_args: str(archive_path))
    server = DummyServer()
    server.data["dir"] = str(install) + "/"
    server.data["exe_name"] = "cod_lnxded"

    mod._stage_gcc3_runtime(server)

    assert (install / "libstdc++.so.5").read_bytes() == b"std"
    assert (install / "libgcc_s.so.1").read_bytes() == b"gcc"

def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "has_start_map", lambda *args: True)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod_lnxded"
    (tmp_path / "cod_lnxded").write_text("")
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "env",
        "LD_LIBRARY_PATH=.",
        "./cod_lnxded",
        "+set",
        "fs_basepath",
        ".",
        "+set",
        "fs_homepath",
        ".",
        "+set",
        "fs_game",
        "test",
        "+set",
        "sv_hostname",
        "test",
        "+set",
        "net_port",
        "27015",
        "+map",
        "test",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_prefers_resolved_nested_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "has_start_map", lambda *args: True)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod_lnxded"
    nested_dir = tmp_path / "serverfiles"
    nested_dir.mkdir()
    nested_exe = nested_dir / "cod_lnxded"
    nested_exe.write_text("", encoding="utf-8")
    (tmp_path / "cod_lnxded").symlink_to(nested_exe)
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "env"
    assert cmd[2] == "./cod_lnxded"
    assert cwd == str(nested_dir)


def test_setting_schema_exposes_cod_launch_tokens():
    assert mod.setting_schema["fs_game"].canonical_key == "moddir"
    assert mod.setting_schema["fs_game"].launch_arg_tokens == ("+set", "fs_game")
    assert mod.setting_schema["hostname"].launch_arg_tokens == ("+set", "sv_hostname")
    assert mod.setting_schema["port"].launch_arg_tokens == ("+set", "net_port")


def test_sync_server_config_updates_mod_server_cfg(tmp_path):
    server = DummyServer("cod")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "moddir": "main",
            "hostname": "AlphaGSM cod",
            "startmap": "mp_harbor",
        }
    )
    cfg_dir = tmp_path / "main"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "server.cfg"
    cfg_path.write_text(
        'hostname="Old Name"\nmoddir=uo\nstartmap=mp_carentan\nset scr_friendlyfire 1\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert cfg_path.read_text(encoding="utf-8") == (
        'hostname="AlphaGSM cod"\n'
        'moddir=main\n'
        'startmap=mp_harbor\n'
        'set scr_friendlyfire 1\n'
    )


def test_has_start_map_accepts_a_pk3_map(tmp_path):
    import zipfile

    main_dir = tmp_path / "main"
    main_dir.mkdir()
    with zipfile.ZipFile(main_dir / "custom_maps.pk3", "w") as archive:
        archive.writestr("maps/mp/mp_harbor.bsp", b"map")

    assert mod.has_start_map(tmp_path, "mp_harbor") is True


def test_get_start_command_requires_owned_multiplayer_map(tmp_path):
    server = DummyServer("cod")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "cod_lnxded",
            "hostname": "test",
            "moddir": "main",
            "port": 27015,
            "startmap": "mp_carentan",
        }
    )
    (tmp_path / "cod_lnxded").write_text("")

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\).*multiplayer map"):
        mod.get_start_command(server)

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()

def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)

def test_message():
    server = DummyServer()
    mod.message(server, "hello")

def test_backup():
    server = DummyServer()
    server.data["dir"] = "/tmp/test/"
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.backup(server)

def test_checkvalue_empty_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ())

def test_checkvalue_unsupported_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")

def test_checkvalue_no_value():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",))

def test_checkvalue_port():
    server = DummyServer()
    result = mod.checkvalue(server, ("port",), "12345")
    assert result == 12345

def test_checkvalue_url():
    server = DummyServer()
    result = mod.checkvalue(server, ("url",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_download_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("download_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_moddir():
    server = DummyServer()
    result = mod.checkvalue(server, ("moddir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
