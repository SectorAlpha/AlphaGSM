"""Setup file selectors and manager-owned Steam profile references."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gamemodules import q3server
from server import ServerError, assets
import server.server as server_module
from server.server import Server
from utils import byo_acquire, byo_files, steam_auth
from utils.cmdparse.cmdparse import parse


class SavedData(dict):
    """Keep persistence observable without writing manager configuration."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save = Mock()


@pytest.fixture
def setup_server(tmp_path, monkeypatch):
    server = Server.__new__(Server)
    server.name = "owned-test"
    server.data = SavedData(dir=str(tmp_path / "server"))
    recipe = {
        "managed_import": True, "roots": [""], "target": "",
        "include": ["baseq3/pak0.pk3"], "required": ["baseq3/pak0.pk3"],
        "requirements": [{"path": "baseq3/pak0.pk3", "kind": "file"}],
        "sources": [{"id": "manual", "kind": "operator-files"},
                    {"id": "steam-owned", "kind": "steamcmd", "app_id": 2200,
                     "platform": "windows", "authentication": "required"}],
    }
    server.module = SimpleNamespace(
        configure=Mock(return_value=(("configured",), {"engine_option": True})),
        install=Mock(), checkvalue=Mock(return_value="unvalidated"),
        sync_server_config=Mock(), postset=Mock(),
        config_sync_keys=("steam_auth_profile",),
        get_asset_requirements=Mock(return_value=recipe),
    )
    monkeypatch.setattr(server, "_explicit_setup_port_keys", Mock(return_value=set()))
    monkeypatch.setattr(server, "_claim_affecting_value_snapshot", Mock(return_value={}))
    monkeypatch.setattr(server, "_resolve_setup_port_claims", Mock())
    for name in ("sync_runtime_metadata", "assert_platform_requirements", "assert_host_install_requirements"):
        monkeypatch.setattr(server_module.runtime_module, name, Mock())
    monkeypatch.setattr(server_module.diagnostics_module, "record_installation_provenance", Mock())
    monkeypatch.setattr(server_module.runtime_module, "get_runtime", lambda _s: SimpleNamespace(is_running=lambda _s: False))
    monkeypatch.setattr(byo_acquire, "acquire", Mock(return_value={"ready": True}))
    return server


def installed_files(server):
    path = Path(server.data["dir"]) / "baseq3/pak0.pk3"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"owned fixture")
    return path


@pytest.mark.parametrize("option,value,key", [
    ("--auth-profile", "owner", "auth_profile"),
    ("--steam-dir", "Steam Library", "steam_dir"),
])
def test_q3_real_combined_setup_parser(option, value, key):
    spec = Server.default_command_args["setup"].combine(q3server.command_args["setup"])
    args, kwargs = parse(["-n", "27960", "server dir", option, value], spec)
    assert args == [27960, "server dir"]
    assert kwargs == {"ask": False, key: value}


@pytest.mark.parametrize("selectors", [
    {"auth_profile": "owner", "assets_source": "files"},
    {"auth_profile": "owner", "steam_dir": "Steam"},
    {"steam_dir": "Steam", "assets_source": "files"},
    {"auth_profile": "owner", "steam_dir": "Steam", "assets_source": "files"},
])
def test_selectors_conflict_before_configure(setup_server, selectors):
    with pytest.raises(ServerError, match="one|exclusive|combine"):
        setup_server.setup(ask=False, **selectors)
    setup_server.module.configure.assert_not_called()
    setup_server.module.install.assert_not_called()
    server_module.runtime_module.sync_runtime_metadata.assert_not_called()


def test_auth_selector_consumed_and_remembered_after_file_phase(setup_server):
    server = setup_server
    server.setup(27960, ask=False, auth_profile="owner", engine="ioquake3")
    server.module.configure.assert_called_once_with(server, False, 27960, engine="ioquake3")
    server.module.install.assert_called_once_with(server, "configured", engine_option=True)
    byo_acquire.acquire.assert_called_once_with(server, server.module.get_asset_requirements.return_value,
                                               "steam-owned", auth_profile="owner")
    assert server.data["steam_auth_profile"] == "owner"
    server.data.save.assert_called_once_with()


def test_saved_profile_retries_missing_files(setup_server):
    server = setup_server
    server.data["steam_auth_profile"] = "saved_owner"
    server.setup(ask=False)
    assert byo_acquire.acquire.call_args.kwargs == {"auth_profile": "saved_owner"}
    server.module.install.assert_called_once()


@pytest.mark.parametrize("saved", [False, True])
def test_native_installed_files_skip_download_and_cache_lookup(setup_server, monkeypatch, saved):
    server = setup_server
    installed_files(server)
    if saved:
        server.data["steam_auth_profile"] = "owner"
    monkeypatch.setattr(steam_auth, "locked_profile", Mock(side_effect=AssertionError("No cache access")))
    server.setup(ask=False, **({} if saved else {"auth_profile": "owner"}))
    byo_acquire.acquire.assert_not_called()
    assert server.data["steam_auth_profile"] == "owner"
    server.data.save.assert_called_once()


def test_native_case_mismatch_does_not_skip_acquisition(setup_server):
    server = setup_server
    path = Path(server.data["dir"]) / "BaseQ3/PAK0.PK3"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong case for native engine")
    server.module.get_asset_requirements.return_value["case_insensitive"] = True
    server.setup(ask=False, auth_profile="owner")
    byo_acquire.acquire.assert_called_once()


def test_no_source_preserves_engine_only_setup(setup_server):
    server = setup_server
    server.module.get_asset_requirements.side_effect = AssertionError("No recipe lookup")
    server.setup(ask=False)
    server.module.install.assert_called_once()
    byo_acquire.acquire.assert_not_called()
    assert "steam_auth_profile" not in server.data


@pytest.mark.parametrize("mode", ["unsupported", "manual", "no-steam", "ambiguous"])
@pytest.mark.parametrize("selector", [{"auth_profile": "owner"}, {"steam_dir": "Steam"}])
def test_unsupported_recipes_never_install(setup_server, mode, selector):
    server = setup_server
    recipe = server.module.get_asset_requirements.return_value
    if mode == "unsupported":
        del server.module.get_asset_requirements
    elif mode == "manual":
        recipe.update(managed_import=False, manual_reason="Manual file staging only")
    elif mode == "no-steam":
        recipe["sources"] = recipe["sources"][:1]
    else:
        recipe["sources"].append(deepcopy(recipe["sources"][-1]))
    with pytest.raises(ServerError):
        server.setup(ask=False, **selector)
    server.module.install.assert_not_called()
    byo_acquire.acquire.assert_not_called()


@pytest.mark.parametrize("selector", [{"auth_profile": "owner"}, {"steam_dir": "Steam"}])
def test_running_server_refuses_file_phase(setup_server, monkeypatch, selector):
    server = setup_server
    monkeypatch.setattr(server_module.runtime_module, "get_runtime", lambda _s: SimpleNamespace(is_running=lambda _s: True))
    with pytest.raises(ServerError, match="stopped"):
        server.setup(ask=False, **selector)
    server.module.install.assert_not_called()
    byo_acquire.acquire.assert_not_called()


def test_failed_acquisition_preserves_profile_and_prevents_install(setup_server):
    server = setup_server
    server.data["steam_auth_profile"] = "old"
    byo_acquire.acquire.side_effect = ServerError("Download rejected")
    with pytest.raises(ServerError, match="Download rejected"):
        server.setup(ask=False, auth_profile="new")
    assert server.data["steam_auth_profile"] == "old"
    server.data.save.assert_not_called()
    server.module.install.assert_not_called()


@pytest.mark.parametrize("profile", ["../secret", "", {"password": "secret"}, ["owner"]])
@pytest.mark.parametrize("saved", [False, True])
def test_invalid_profile_never_downloads_or_installs(setup_server, profile, saved):
    server = setup_server
    if saved:
        server.data["steam_auth_profile"] = profile
    with pytest.raises(ServerError, match="profile name"):
        server.setup(ask=False, **({} if saved else {"auth_profile": profile}))
    server.module.install.assert_not_called()
    byo_acquire.acquire.assert_not_called()


@pytest.mark.parametrize("source_kind", ["assets", "steam"])
def test_explicit_local_import_overrides_saved_profile_without_changing_source(setup_server, tmp_path, source_kind):
    server = setup_server
    server.data["steam_auth_profile"] = "saved_owner"
    library = tmp_path / "SteamLibrary"
    game = library / "steamapps/common/Owned Game"
    (game / "baseq3").mkdir(parents=True)
    (game / "baseq3/pak0.pk3").write_bytes(b"owned fixture")
    (game / "account-password.txt").write_bytes(b"never import")
    (library / "steamapps/appmanifest_2200.acf").write_text(
        '"AppState" { "appid" "2200" "installdir" "Owned Game" }')
    # This unrelated manifest must never be used to infer the requested app.
    (library / "steamapps/appmanifest_999.acf").write_text('"malformed unrelated metadata"')
    before = {str(path.relative_to(library)): path.read_bytes() for path in library.rglob("*") if path.is_file()}
    options = {"assets_source": str(game)} if source_kind == "assets" else {"steam_dir": str(library)}
    server.setup(ask=False, **options)
    assert (Path(server.data["dir"]) / "baseq3/pak0.pk3").read_bytes() == b"owned fixture"
    assert not (Path(server.data["dir"]) / "account-password.txt").exists()
    assert before == {str(path.relative_to(library)): path.read_bytes() for path in library.rglob("*") if path.is_file()}
    assert server.data["steam_auth_profile"] == "saved_owner"
    server.data.save.assert_not_called()
    byo_acquire.acquire.assert_not_called()
    server.module.configure.assert_called_once_with(server, False)
    server.module.install.assert_called_once_with(server, "configured", engine_option=True)


def test_steam_directory_uses_declared_app_id_only(setup_server, tmp_path):
    library = tmp_path / "Steam"
    apps = library / "steamapps"
    (apps / "common/Other Game").mkdir(parents=True)
    (apps / "appmanifest_999.acf").write_text('"AppState" { "appid" "999" "installdir" "Other Game" }')
    with pytest.raises(ServerError, match="app ID"):
        setup_server.setup(ask=False, steam_dir=str(library))
    setup_server.module.install.assert_not_called()


def test_manager_profile_set_replaces_and_deletes_without_game_hooks(setup_server):
    server = setup_server
    server.data["steam_auth_profile"] = "old"
    server.doset("steam_auth_profile", "owner")
    assert server.data["steam_auth_profile"] == "owner"
    server.doset("steam_auth_profile", "DELETE")
    server.doset("steam_auth_profile", "DELETE")
    assert "steam_auth_profile" not in server.data
    assert server.data.save.call_count == 3
    server.module.checkvalue.assert_not_called()
    server.module.sync_server_config.assert_not_called()
    server.module.postset.assert_not_called()


@pytest.mark.parametrize("key,args", [
    ("steam_auth_profile", ()),
    ("steam_auth_profile", ("one", "two")),
    ("steam_auth_profile", ("../secret",)),
    ("steam_auth_profile", ({"password": "secret"},)),
    ("steam_auth_profile.password", ("secret",)),
    ("steam_auth_profile.APPEND", ("owner",)),
])
def test_manager_profile_set_rejects_invalid_and_nested_values(setup_server, key, args):
    server = setup_server
    with pytest.raises(ServerError):
        server.doset(key, *args)
    assert "steam_auth_profile" not in server.data
    server.data.save.assert_not_called()
    server.module.checkvalue.assert_not_called()
    server.module.sync_server_config.assert_not_called()
    server.module.postset.assert_not_called()


def test_manager_profile_set_rejects_ineligible_module(setup_server):
    server = setup_server
    server.module.get_asset_requirements.return_value["managed_import"] = False
    with pytest.raises(ServerError):
        server.doset("steam_auth_profile", "owner")
    server.data.save.assert_not_called()
    server.module.checkvalue.assert_not_called()


def test_public_profile_validator_shares_existing_name_rules():
    steam_auth.validate_profile_name("owner_Name-12")
    with pytest.raises(steam_auth.SteamAuthError, match="Invalid SteamCMD profile name"):
        steam_auth.validate_profile_name("../secret")


def test_manager_profile_delete_clears_stale_reference_on_unsupported_module(setup_server):
    server = setup_server
    server.data["steam_auth_profile"] = "stale"
    del server.module.get_asset_requirements
    server.doset("steam_auth_profile", "DELETE")
    assert "steam_auth_profile" not in server.data
    server.data.save.assert_called_once()
    server.module.checkvalue.assert_not_called()


@pytest.mark.parametrize("selector", [{"auth_profile": "owner"}, {"steam_dir": "Steam"}])
def test_steam_selectors_require_explicit_managed_recipe(setup_server, selector):
    server = setup_server
    del server.module.get_asset_requirements.return_value["managed_import"]
    with pytest.raises(ServerError, match="managed"):
        server.setup(ask=False, **selector)
    server.module.install.assert_not_called()
    byo_acquire.acquire.assert_not_called()


def test_manager_profile_requires_explicit_managed_recipe(setup_server):
    server = setup_server
    del server.module.get_asset_requirements.return_value["managed_import"]
    with pytest.raises(ServerError, match="managed"):
        server.doset("steam_auth_profile", "owner")
    server.data.save.assert_not_called()


@pytest.mark.parametrize("guard", ["assert_platform_requirements", "assert_host_install_requirements"])
def test_setup_guards_precede_file_acquisition(setup_server, monkeypatch, guard):
    server = setup_server
    monkeypatch.setattr(server_module.runtime_module, guard,
                        Mock(side_effect=server_module.runtime_module.RuntimeError("Unsupported host")))
    with pytest.raises(ServerError, match="Unsupported host"):
        server.setup(ask=False, auth_profile="owner")
    server.module.configure.assert_called_once()
    byo_acquire.acquire.assert_not_called()
    server.module.install.assert_not_called()
    server.data.save.assert_not_called()


def test_auth_file_phase_requires_install_directory(setup_server):
    server = setup_server
    del server.data["dir"]
    with pytest.raises(ServerError, match="installation directory"):
        server.setup(ask=False, auth_profile="owner")
    byo_acquire.acquire.assert_not_called()
    server.module.install.assert_not_called()
    server.data.save.assert_not_called()
