"""ARK compressed content, binary descriptor and native activation regressions."""

from importlib import import_module
import struct
import zlib

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def fstring(value):
    """Build fixture metadata in Unreal's documented ANSI string representation."""
    raw = value.encode() + b"\0"
    return struct.pack("<I", len(raw)) + raw


def make_adapter(tmp_path, monkeypatch):
    """Use genuine chunk headers and small native metadata inside the server root."""
    adapter = import_module("gamemodules.ark.workshop")
    server = DummyServer("arkworkshop")
    server.data["dir"] = str(tmp_path)
    payload = tmp_path / ".alphagsm/fixtures/111/LinuxNoEditor"
    payload.mkdir(parents=True)
    content = b"native-content-" * 10
    compressed = [zlib.compress(content[:75]), zlib.compress(content[75:])]
    header = struct.pack("<4Q", 0x9E2A83C1, 75, sum(map(len, compressed)), len(content))
    header += struct.pack("<4Q", len(compressed[0]), 75, len(compressed[1]), len(content)-75)
    (payload / "Example.uasset.z").write_bytes(header + b"".join(compressed))
    (payload / "Example.uasset.z.uncompressed_size").write_text(str(len(content)))
    (payload / "mod.info").write_bytes(fstring("Example") + struct.pack("<I", 2)
                                        + fstring("FirstMap") + fstring("SecondMap") + b"\0" * 8)
    (payload / "modmeta.info").write_bytes(struct.pack("<I", 1) + fstring("ModType") + fstring("1"))
    monkeypatch.setattr(adapter, "download_workshop_items", lambda _server, app, ids: {
        item: payload.parent for item in ids if app == 346110})
    return adapter, server, payload, content


def test_decompressed_native_files_descriptor_and_operator_ids(tmp_path, monkeypatch):
    adapter, server, payload, content = make_adapter(tmp_path, monkeypatch)
    config = tmp_path / "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini"
    config.parent.mkdir(parents=True)
    config.write_text("; retain\n[ServerSettings]\nActiveMods=999\nDifficultyOffset=0.5\n[Other]\nFoo=bar\n")
    adapter.configure_workshop(server, ["111"])
    native = tmp_path / "ShooterGame/Content/Mods"
    assert (native / "111/Example.uasset").read_bytes() == content
    assert not (native / "111/Example.uasset.z").exists()
    descriptor = (native / "111.mod").read_bytes()
    assert struct.unpack("<Q", descriptor[:8])[0] == 111
    assert descriptor.endswith(b"\x33\xff\x22\xff\x02\0\0\0\x01" + (payload / "modmeta.info").read_bytes())
    assert fstring("FirstMap") + fstring("SecondMap") in descriptor
    assert "ActiveMods=999,111" in config.read_text()
    adapter.configure_workshop(server, [])
    assert "ActiveMods=999" in config.read_text()
    assert "; retain" in config.read_text() and "Foo=bar" in config.read_text()
    assert not (native / "111.mod").exists()


def test_bad_compressed_stream_does_not_activate_or_publish(tmp_path, monkeypatch):
    adapter, server, payload, _content = make_adapter(tmp_path, monkeypatch)
    compressed = payload / "Example.uasset.z"
    compressed.write_bytes(compressed.read_bytes()[:-2])
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    assert not (tmp_path / "ShooterGame/Content/Mods/111.mod").exists()
    assert not (tmp_path / "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini").exists()


def test_size_claim_and_bad_metadata_rejected(tmp_path, monkeypatch):
    adapter, server, payload, _content = make_adapter(tmp_path, monkeypatch)
    compressed = payload / "Example.uasset.z"
    raw = compressed.read_bytes()
    compressed.write_bytes(raw[:24] + struct.pack("<Q", 2**63) + raw[32:])
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    compressed.write_bytes(raw)
    (payload / "mod.info").write_bytes(struct.pack("<I", 2**31))
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])


def test_publication_failure_rolls_back_ini_and_native_ownership(tmp_path, monkeypatch):
    adapter, server, _payload, _content = make_adapter(tmp_path, monkeypatch)
    adapter.configure_workshop(server, ["111"])
    def fail(*_args):
        raise OSError("disk full")
    monkeypatch.setattr(adapter, "publish_owned_payloads", fail)
    with pytest.raises(OSError):
        adapter.configure_workshop(server, [])
    config = tmp_path / "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini"
    assert "ActiveMods=111" in config.read_text()
    assert server.data["mods"]["ark_workshop_ids"] == ["111"]


def test_launch_includes_native_mod_ids_even_when_first_boot_regenerates_ini(tmp_path, monkeypatch):
    """The URL must carry staged mods before ARK's first-boot config rewrite."""
    adapter, server, _payload, _content = make_adapter(tmp_path, monkeypatch)
    module = import_module("gamemodules.ark")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    executable = tmp_path / "ShooterGame/Binaries/Linux/ShooterGameServer"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    config = tmp_path / "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini"
    config.parent.mkdir(parents=True)
    config.write_text("[ServerSettings]\nActiveMods=999\n")
    adapter.configure_workshop(server, ["111"])
    command, _directory = module.get_start_command(server)
    assert "?GameModIds=999,111" in command[1]
    adapter.configure_workshop(server, [])
    command, _directory = module.get_start_command(server)
    assert "?GameModIds=999" in command[1] and "111" not in command[1]
