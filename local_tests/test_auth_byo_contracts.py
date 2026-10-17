"""Local unit checks for AUTH and BYO servers. No Steam login and no downloads."""

import importlib
import json
from pathlib import Path
import zipfile

import pytest

from catalog import REPO_ROOT, auth_servers, byo_servers


FILE_BYO_CATEGORIES = {"assets", "export"}
SECRET_MARKERS = ("password =", "token =", "guard code", "ssfn")
# Ratchet: remove a name when that module declares get_provider_requirements.
MISSING_PROVIDER_HOOKS = frozenset({
    "arma2coserver",
    "arma3server",
    "arma3altislifeserver",
    "arma3desolationreduxserver",
    "arma3epochserver",
    "arma3exileserver",
    "arma3headlessserver",
    "arma3wastelandserver",
    "dayzarma2epochserver",
    "dayzserver",
    "ducksideserver",
    "hellletlooseserver",
    "motortownserver",
    "reignofkingsserver",
    "ror2server",
    "staxelserver",
    "brickadiaserver",
    "interstellarriftserver",
    "twserver",
    "accserver",
    "boserver",
    "deadmatterserver",
    "kfserver",
    "mw3server",
    "police1013server",
    "pcars2server",
    "roserver",
    "bannerlordserver",
    "chivalryserver",
    "brokeprotocolserver",
    "bsserver",
    "dabserver",
    "dysserver",
    "iosserver",
    "zpsserver",
    "arma3.altislife",
    "arma3.desolationredux",
    "arma3.epoch",
    "arma3.exile",
    "arma3.headless",
    "arma3.vanilla",
    "arma3.wasteland",
})


def _import_module(module_name):
    return importlib.import_module("gamemodules." + module_name)


def _manifest(module):
    return Path(module.__file__).with_name("byo_assets.json")


@pytest.mark.parametrize("row", auth_servers(), ids=lambda row: row["module"])
def test_auth_server_imports_and_declares_its_provider_category(row):
    module = _import_module(row["module"])
    hook = getattr(module, "get_provider_requirements", None)
    if hook is None:
        assert row["module"] in MISSING_PROVIDER_HOOKS
        return
    assert row["module"] not in MISSING_PROVIDER_HOOKS
    requirements = list(hook(type("Server", (), {"data": {}, "name": "local"})()))
    assert requirements, row["module"] + " declared no provider requirements"
    categories = {item.get("support_category") for item in requirements}
    assert row["category"] in categories
    for requirement in requirements:
        encoded = json.dumps(requirement, default=str).lower()
        for marker in SECRET_MARKERS:
            assert marker not in encoded


@pytest.mark.parametrize("row", byo_servers(), ids=lambda row: "byo-" + row["module"])
def test_byo_server_imports_and_file_categories_have_a_recipe(row):
    module = _import_module(row["module"])
    assert row["reason"]
    if row["category"] not in FILE_BYO_CATEGORIES:
        return
    manifest = _manifest(module)
    assert manifest.is_file(), row["module"] + " is missing byo_assets.json"
    recipe = json.loads(manifest.read_text(encoding="utf-8"))
    assert recipe.get("requirements"), row["module"] + " recipe has no requirements"
    encoded = json.dumps(recipe).lower()
    for marker in SECRET_MARKERS:
        assert marker not in encoded


def _concrete_pattern(pattern):
    return pattern.replace("*", "mpasset").replace("?", "a")


def _write_server_payload(path, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".pk3", ".iwd", ".zip"}:
        with zipfile.ZipFile(path, "w") as archive:
            for member in members:
                archive.writestr(member, b"map")
        return
    path.write_bytes(b"server-content")


def test_managed_import_keeps_server_content_and_drops_client_files(tmp_path):
    """A mixed owned tree publishes only recipe includes, not client or movie files."""

    from utils import asset_import

    junk_names = (
        "CoDMP.exe",
        "CoDSP.exe",
        "movies/intro.bik",
        "redist/dxsetup.exe",
        "Install/setup.exe",
        "main/singleplayer.sav",
    )
    for row in byo_servers():
        module = _import_module(row["module"])
        if not hasattr(module, "get_asset_requirements"):
            continue
        server = type("Server", (), {"data": {"dir": str(tmp_path), "name": "local"}, "name": "local"})()
        recipe = module.get_asset_requirements(server)
        if not recipe.get("managed_import"):
            continue
        source = tmp_path / row["module"] / "owned"
        install = tmp_path / row["module"] / "server"
        source.mkdir(parents=True)
        install.mkdir()
        for name in junk_names:
            path = source.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"client")
        patterns = list(recipe.get("include", []))
        for group in recipe.get("required", []):
            patterns.append(group)
        for group in recipe.get("required_any", []):
            patterns.append(group[0])
        members = ["maps/mp/mp_carentan.bsp", "maps/mp/mpasset.bsp", "maps/mp/mp_brecourt.bsp"]
        for requirement in recipe.get("requirements", []):
            for member in requirement.get("member_any_of") or []:
                members.append(str(member))
        for pattern in patterns:
            relative = _concrete_pattern(str(pattern))
            _write_server_payload(source.joinpath(*relative.split("/")), members)
        report = asset_import.import_assets(source, install, recipe)
        published = [name.replace("\\", "/").lower() for name in report["copied"]]
        assert published, row["module"] + " published no server files"
        for name in published:
            assert not name.endswith((".exe", ".bik", ".sav", ".msi", ".dll")), (row["module"], name)
            assert not name.startswith(("movies/", "redist/", "install/")), (row["module"], name)
            assert "codmp.exe" not in name
            assert "singleplayer" not in name


def test_local_tree_contains_no_auth_material():
    root = REPO_ROOT / "local_tests"
    blocked = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"profile.json", "config.vdf"} or path.name.startswith("ssfn"):
            blocked.append(str(path.relative_to(REPO_ROOT)))
    assert blocked == []
