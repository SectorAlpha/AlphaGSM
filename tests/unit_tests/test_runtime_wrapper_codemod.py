import sys

from tests.helpers import load_module_from_repo


module_family_map = load_module_from_repo(
    "runtime_contract_module_family_map",
    "scripts/runtime_contract/module_family_map.py",
)
sys.modules["module_family_map"] = module_family_map
codemod_module = load_module_from_repo(
    "runtime_contract_apply_module_runtime_wrappers",
    "scripts/runtime_contract/apply_module_runtime_wrappers.py",
)


def test_module_family_map_loads_and_resolves_patterns():
    manifest = module_family_map.load_module_family_map()

    assert manifest["alienarenaserver"]["family"] == "steamcmd-linux"
    assert manifest["askaserver"]["builder"] == "proton"
    assert module_family_map.resolve_module_family("minecraft.vanilla")[
        "family"
    ] == "java"
    assert module_family_map.module_patterns_for_family("java") == (
        "minecraft.vanilla",
        "minecraft.bungeecord",
    )
    assert "wine-proton" in module_family_map.known_families()


def test_apply_module_runtime_wrappers_inserts_runtime_import_and_wrappers(tmp_path):
    module_path = tmp_path / "sample.py"
    module_path.write_text(
        "import os\n\n"
        "def get_start_command(server):\n"
        "    return ['server'], server.data['dir']\n",
        encoding="utf-8",
    )

    source = module_path.read_text(encoding="utf-8")
    result = codemod_module.apply_wrappers_to_source(
        source,
        family="steamcmd-linux",
        port_definitions=(("port", "udp"),),
    )

    assert "import server.runtime as runtime_module" in result
    assert "def get_runtime_requirements(server):" in result
    assert "def get_container_spec(server):" in result
    assert "family='steamcmd-linux'" in result

    assert (
        codemod_module.apply_wrappers_to_source(
            result,
            family="steamcmd-linux",
            port_definitions=(("port", "udp"),),
        )
        == result
    )


def test_apply_module_runtime_wrappers_supports_dict_port_definitions():
    source = (
        "def get_start_command(server):\n"
        "    return ['server'], server.data['dir']\n"
    )

    result = codemod_module.apply_wrappers_to_source(
        source,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "clientport", "protocol": "udp"},
        ),
    )

    assert "{'key': 'port', 'protocol': 'udp'}" in result
    assert "{'key': 'clientport', 'protocol': 'udp'}" in result


def test_apply_module_runtime_wrappers_supports_alias_modules():
    source = 'ALIAS_TARGET = "teamfortress2"\n'

    result = codemod_module.apply_wrappers_to_source(
        source,
        family="steamcmd-linux",
        builder="alias",
    )

    assert "from importlib import import_module" in result
    assert '_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)' in result
    assert "def get_runtime_requirements(server):" in result
    assert "return _ALIAS_MODULE.get_runtime_requirements(server)" in result
    assert "def get_container_spec(server):" in result
    assert "return _ALIAS_MODULE.get_container_spec(server)" in result


def test_apply_module_runtime_wrappers_supports_java_family():
    source = (
        "def get_start_command(server):\n"
        "    return ['java', '-jar', server.data['exe_name'], 'nogui'], server.data['dir']\n"
    )

    result = codemod_module.apply_wrappers_to_source(
        source,
        family="java",
        port_definitions=(("port", "tcp"),),
        builder="java",
    )

    assert "java_major = server.data.get(\"java_major\")" in result
    assert "runtime_module.infer_minecraft_java_major" in result
    assert "\"ALPHAGSM_JAVA_MAJOR\": str(java_major)" in result
    assert "extra={\"java\": int(java_major)}" in result
    assert "env=requirements.get(\"env\", {})" in result


def test_apply_module_runtime_wrappers_inserts_import_after_multiline_from_import():
    source = (
        "from package import (\n"
        "    one,\n"
        "    two,\n"
        ")\n\n"
        "def get_start_command(server):\n"
        "    return ['server'], server.data['dir']\n"
    )

    result = codemod_module.apply_wrappers_to_source(
        source,
        family="steamcmd-linux",
        port_definitions=(("port", "udp"),),
    )

    assert "from package import (\n    one,\n    two,\n)\nimport server.runtime as runtime_module" in result
    assert "from package import (\nimport server.runtime as runtime_module" not in result
