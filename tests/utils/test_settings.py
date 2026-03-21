import importlib

import pytest

import utils.settings._settings as settings_module


@pytest.fixture
def reset_settings_singleton():
    cls = settings_module.Settings
    old_instance = getattr(cls, "_instance", None)
    if hasattr(cls, "_instance"):
        delattr(cls, "_instance")
    yield
    if hasattr(cls, "_instance"):
        delattr(cls, "_instance")
    if old_instance is not None:
        cls._instance = old_instance


def test_empty_mapping_behaves_like_empty_mapping():
    mapping = settings_module.EmptyMapping(default="fallback")

    assert len(mapping) == 0
    assert list(mapping) == []
    assert "missing" not in mapping
    assert mapping.get("missing") == "fallback"
    assert mapping.get("missing", "explicit") == "explicit"
    assert str(mapping) == "{}"


def test_settings_section_exposes_values_and_subsections():
    child = settings_module.SettingsSection({}, {"value": "child"})
    section = settings_module.SettingsSection({"child": child}, {"root": "yes"})

    assert section["root"] == "yes"
    assert section.get("missing", "fallback") == "fallback"
    assert section.child is child
    assert section.getsection("child") is child
    assert section.getsection("missing") is settings_module._emptysection

    with pytest.raises(AttributeError):
        _ = section.missing


def test_loadsettings_merges_parent_values_and_subsections(tmp_path):
    parent_path = tmp_path / "parent.conf"
    child_path = tmp_path / "child.conf"
    parent_path.write_text("[core]\nmode=prod\n[core.paths]\nroot=/srv/app\n")
    child_path.write_text("[core]\nname=alpha\n")

    parent = settings_module._loadsettings(str(parent_path))
    merged = settings_module._loadsettings(str(child_path), parent)

    assert merged.getsection("core")["name"] == "alpha"
    assert merged.getsection("core")["mode"] == "prod"
    assert merged.getsection("core").getsection("paths")["root"] == "/srv/app"


def test_loadsettings_returns_parent_if_child_is_missing(tmp_path):
    parent_path = tmp_path / "parent.conf"
    parent_path.write_text("[core]\nmode=prod\n")
    parent = settings_module._loadsettings(str(parent_path))

    merged = settings_module._loadsettings(str(tmp_path / "missing.conf"), parent)

    assert merged is parent


def test_settings_reads_system_and_user_files_from_environment(tmp_path, monkeypatch, reset_settings_singleton):
    system_path = tmp_path / "system.conf"
    user_dir = tmp_path / "user-dir"
    user_dir.mkdir()
    user_path = user_dir / "alphagsm.conf"

    system_path.write_text(
        "[core]\n"
        f"userconf={user_dir}\n"
        "alphagsm_path=/system/path\n"
        "[server]\n"
        "datapath=/system/data\n"
    )
    user_path.write_text("[core]\nalphagsm_path=/user/path\n")

    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", str(system_path))
    monkeypatch.delenv("ALPHAGSM_USERCONFIG_LOCATION", raising=False)

    settings = settings_module.Settings()

    assert settings.system.getsection("server")["datapath"] == "/system/data"
    assert settings.user.getsection("core")["alphagsm_path"] == "/user/path"
    assert settings.user.getsection("server")["datapath"] == "/system/data"


def test_settings_honors_explicit_user_config_override(tmp_path, monkeypatch, reset_settings_singleton):
    system_path = tmp_path / "system.conf"
    user_path = tmp_path / "override.conf"

    system_path.write_text("[core]\nuserconf=/unused\n")
    user_path.write_text("[feature]\nflag=enabled\n")

    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", str(system_path))
    monkeypatch.setenv("ALPHAGSM_USERCONFIG_LOCATION", str(user_path))

    settings = settings_module.Settings()

    assert settings.user.getsection("feature")["flag"] == "enabled"


def test_utils_settings_reexports_the_singleton():
    public_module = importlib.import_module("utils.settings")

    assert public_module.settings is settings_module.settings
