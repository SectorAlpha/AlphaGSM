"""Local unit checks for AUTH and BYO servers. No Steam login and no downloads."""

import importlib
import json
from pathlib import Path

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


def test_local_tree_contains_no_auth_material():
    root = REPO_ROOT / "local_tests"
    blocked = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"profile.json", "config.vdf"} or path.name.startswith("ssfn"):
            blocked.append(str(path.relative_to(REPO_ROOT)))
    assert blocked == []
