"""Coverage for AlphaGSM-oriented server-template defaults."""

from collections import OrderedDict

import utils.server_template_defaults as mod


def test_extract_template_defaults_for_representative_modules():
    assert mod.extract_template_defaults("nightingale") == OrderedDict(
        [
            ("savegame", "<server name>"),
            ("port", 7777),
        ]
    )
    assert mod.extract_template_defaults("mxbikesserver") == OrderedDict(
        [
            ("port", 54210),
        ]
    )
    assert mod.extract_template_defaults("arma3-headless") == OrderedDict(
        [
            ("profilesdir", "profiles"),
            ("connect", "127.0.0.1"),
            ("password", ""),
            ("mod", ""),
            ("port", 2302),
        ]
    )
    assert mod.extract_template_defaults("risingstorm2vietnam") == OrderedDict(
        [
            ("queryport", "27015"),
            ("configfile", "ROGame/Config/PCServer-ROGame.ini"),
            ("port", 7777),
        ]
    )
    assert mod.extract_template_defaults("necserver") == OrderedDict(
        [
            ("servername", "AlphaGSM <server name>"),
            ("slots", "10"),
            ("world", "<server name>"),
            ("javapath", "java"),
            ("port", 14159),
        ]
    )


def test_extract_runtime_template_path_for_verified_modules():
    assert mod.extract_runtime_template_path("risingstorm2vietnam").as_posix() == "ROGame/Config/PCServer-ROGame.ini"
    assert mod.extract_runtime_template_path("starbound").as_posix() == "storage/starbound_server.config"
    assert mod.extract_runtime_template_path("nightingale").as_posix() == "NWX/Config/ServerSettings.ini"
    assert mod.extract_runtime_template_path("enshrouded").as_posix() == "enshrouded_server.json"
    assert mod.extract_runtime_template_path("interstellarriftserver").as_posix() == "server.json"
    assert (
        mod.extract_runtime_template_path("pathoftitansserver").as_posix()
        == "PathOfTitans/Saved/Config/WindowsServer/Game.ini"
    )


def test_all_alphagsm_templates_include_supported_module_defaults():
    missing = {}
    for template_path in mod.iter_alphagsm_example_templates():
        expected = mod.extract_template_defaults(template_path.parent.name)
        present = mod.parse_template_assignments(template_path.read_text())
        absent = [key for key in expected if key not in present]
        if absent:
            missing[template_path.parent.name] = absent

    assert missing == {}


def test_only_non_runtime_examples_keep_generic_template_filename():
    offenders = {}
    for template_path in mod.iter_alphagsm_example_templates():
        runtime_path = mod.extract_runtime_template_path(template_path.parent.name)
        if runtime_path is not None:
            offenders[template_path.parent.name] = runtime_path.as_posix()

    assert offenders == {}
