"""Pinned server-framework manifests install into the dedicated-server tree."""

from pathlib import Path
import zipfile

import gamemodules.counterstrike2 as cs2
import gamemodules.hurtworldserver as hurtworld
import gamemodules.palworld as palworld
import gamemodules.projectzomboid as projectzomboid
import gamemodules.reignofkingsserver as reignofkings
import gamemodules.ror2server as ror2
import gamemodules.rust as rust
import gamemodules.sonsoftheforestserver as sons
import gamemodules.theforestserver as theforest
import gamemodules.valheim as valheim
import server.modsupport.source_addons as source_addons


class DummyData(dict):
    def save(self):
        return None


def test_framework_manifests_resolve_pinned_releases():
    oxide = rust.load_curated_registry().resolve("oxide")
    assert oxide.url.endswith("/2.0.7830/Oxide.Rust-linux.zip")
    bepinex = valheim.load_curated_registry().resolve("bepinex")
    assert bepinex.url.endswith("/BepInEx_linux_x64_5.4.23.5.zip")
    frameworks = cs2.load_curated_registry().resolve_with_dependencies("counterstrikesharp")
    assert [item.family for item in frameworks] == ["metamod", "counterstrikesharp"]
    assert "mmsource-2.0.0-git1483-linux.tar.gz" in frameworks[0].url
    shared = source_addons.load_shared_source_curated_registry()
    steamworks = shared.resolve_with_dependencies("steamworks")
    assert [item.family for item in steamworks] == ["sourcemod", "steamworks"]
    assert hurtworld.load_curated_registry().resolve("oxide").url.endswith("Oxide.Hurtworld-linux.zip")
    assert theforest.load_curated_registry().resolve("oxide").url.endswith("Oxide.TheForest.zip")
    assert reignofkings.load_curated_registry().resolve("oxide").url.endswith("Oxide.ReignOfKings.zip")
    assert ror2.load_curated_registry().resolve("bepinex").url.endswith("BepInEx_win_x64_5.4.23.5.zip")
    assert sons.load_curated_registry().resolve("bepinex").url.endswith("BepInEx_win_x64_5.4.23.5.zip")


def test_soft_wipe_paths_leave_configuration_directories():
    server = DummyData()
    assert palworld.get_wipe_paths(server) == ["Pal/Saved/SaveGames"]
    assert palworld.get_hard_wipe_preserve_paths(server) == ["Pal/Saved/Config"]
    assert valheim.get_wipe_paths(server) == ["worlds"]
    assert "adminlist.txt" in valheim.get_hard_wipe_preserve_paths(server)
    assert projectzomboid.get_wipe_paths(server) == ["Zomboid/Saves"]
    assert projectzomboid.get_hard_wipe_preserve_paths(server) == ["Zomboid/Server"]


def test_rust_oxide_apply_stages_owned_framework_files(tmp_path, monkeypatch):
    archive = tmp_path / "oxide.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("oxide/oxide.config.json", "{}\n")
        handle.writestr("RustDedicated_Data/Managed/Assembly-CSharp.dll", "patched")

    def download(url, allowed_hosts, target_path, checksum=None):
        del url, allowed_hosts, checksum
        Path(target_path).write_bytes(archive.read_bytes())

    monkeypatch.setattr(source_addons, "download_to_cache", download)
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    server = type("Server", (), {"name": "rust", "data": DummyData(dir=str(server_dir))})()

    rust.command_functions["mod"](server, "add", "manifest", "oxide")
    rust.command_functions["mod"](server, "apply")

    assert (server_dir / "oxide" / "oxide.config.json").read_text() == "{}\n"
    assert (server_dir / "RustDedicated_Data" / "Managed" / "Assembly-CSharp.dll").read_text() == "patched"


def test_framework_replace_restores_the_original_game_file_on_cleanup(tmp_path, monkeypatch):
    archive = tmp_path / "oxide.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("Hurtworld_Data/Managed/Assembly-CSharp.dll", "patched")
        handle.writestr("Hurtworld_Data/Managed/Oxide.Core.dll", "framework")

    def download(url, allowed_hosts, target_path, checksum=None):
        del url, allowed_hosts, checksum
        Path(target_path).write_bytes(archive.read_bytes())

    monkeypatch.setattr(source_addons, "download_to_cache", download)
    server_dir = tmp_path / "server"
    managed = server_dir / "Hurtworld_Data" / "Managed"
    managed.mkdir(parents=True)
    original = managed / "Assembly-CSharp.dll"
    original.write_text("vanilla")
    server = type("Server", (), {"name": "hurt", "data": DummyData(dir=str(server_dir))})()

    hurtworld.command_functions["mod"](server, "add", "manifest", "oxide")
    hurtworld.command_functions["mod"](server, "apply")
    assert original.read_text() == "patched"
    assert (managed / "Oxide.Core.dll").read_text() == "framework"

    hurtworld.command_functions["mod"](server, "cleanup")
    assert original.read_text() == "vanilla"
    assert not (managed / "Oxide.Core.dll").exists()


def test_valheim_start_uses_bepinex_when_the_script_is_installed(tmp_path):
    script = tmp_path / "run_bepinex.sh"
    script.write_text('executable_name=""\nexec "$executable_name" "$@"\n')
    (tmp_path / "valheim_server.x86_64").write_text("")
    server = type("Server", (), {"data": {
        "dir": str(tmp_path) + "/",
        "exe_name": "valheim_server.x86_64",
        "port": 2456,
        "public": "0",
        "servername": "AlphaGSM valheim",
        "serverpassword": "alphagsm",
        "worldname": "myworld",
    }})()

    command, _cwd = valheim.get_start_command(server)

    assert command[0] == "./run_bepinex.sh"
    assert 'executable_name="valheim_server.x86_64"' in script.read_text()
