"""Static contract tests for Docker runtime metadata coverage."""

import os
from importlib import import_module
from pathlib import Path

import server.runtime as runtime_module


GAMEMODULE_DIR = Path("src/gamemodules")
HELPER_MODULES = {
    "factorio",
    "minecraft.jardownload",
    "minecraft.papermc",
    "terraria.common",
}


def _game_module_names():
    names = []
    for path in sorted(GAMEMODULE_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        module_name = ".".join(path.relative_to(GAMEMODULE_DIR).with_suffix("").parts)
        if module_name in HELPER_MODULES:
            continue
        names.append(module_name)
    return names


def _module_source(module_name):
    """Return the source text for a game module."""

    path = GAMEMODULE_DIR.joinpath(*module_name.split(".")).with_suffix(".py")
    return path.read_text(encoding="utf-8")


class _DataStore(dict):
    def save(self):
        return None


class _FakeServer:
    def __init__(self, name, base_dir):
        self.name = name
        self.data = _DataStore(dir=str(base_dir / "server") + "/")
        self.module = None


def _resolve_module(module):
    while hasattr(module, "ALIAS_TARGET"):
        module = import_module("gamemodules." + module.ALIAS_TARGET)
    return module


def _stub_download_resolution(module, module_name):
    originals = {}

    def _fake_resolve_download(*args, **kwargs):
        version = kwargs.get("version")
        if version is None and args:
            version = args[-1]
        resolved = str(version or "test")
        download_name = "%s.zip" % (module_name.replace(".", "-"),)
        url = "https://example.invalid/%s" % (download_name,)
        if module_name == "goldeneyesourceserver":
            return resolved, download_name, url
        return resolved, url

    for attribute_name in dir(module):
        original = getattr(module, attribute_name, None)
        if not callable(original):
            continue
        if (
            ("resolve" not in attribute_name or "download" not in attribute_name)
            and "file_url" not in attribute_name
        ):
            continue
        originals[attribute_name] = original
        if "file_url" in attribute_name:
            setattr(
                module,
                attribute_name,
                lambda *args, **kwargs: "https://example.invalid/%s.zip"
                % (module_name.replace(".", "-"),),
            )
        else:
            setattr(module, attribute_name, _fake_resolve_download)

    return originals


def _seed_install_state(server):
    root = Path(server.data["dir"])
    root.mkdir(parents=True, exist_ok=True)

    exe_name = server.data.get("exe_name")
    if exe_name:
        exe_path = root / exe_name
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        exe_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(exe_path, 0o755)
        if exe_name == "srcds_run":
            alt_path = root / "srcds_run_64"
            alt_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(alt_path, 0o755)

    configfile = server.data.get("configfile")
    if configfile:
        config_path = root / configfile
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            config_path.write_text("{}\n", encoding="utf-8")

    profilesdir = server.data.get("profilesdir")
    if profilesdir:
        (root / profilesdir).mkdir(parents=True, exist_ok=True)


def _default_test_port(module_name):
    if module_name.startswith("minecraft."):
        return 25565
    return 27015


def test_all_game_modules_define_explicit_runtime_wrappers():
    offenders = []
    for module_name in _game_module_names():
        source = _module_source(module_name)
        if "import server.runtime as runtime_module" not in source:
            offenders.append(module_name + ": missing runtime_module import")
        if "def get_runtime_requirements(" not in source:
            offenders.append(module_name + ": missing get_runtime_requirements")
        if "def get_container_spec(" not in source:
            offenders.append(module_name + ": missing get_container_spec")
    assert offenders == []


def test_all_game_modules_resolve_valid_docker_manifests():
    offenders = []
    for module_name in _game_module_names():
        module = _resolve_module(import_module("gamemodules." + module_name))
        original_resolvers = _stub_download_resolution(module, module_name)
        server = _FakeServer("it-" + module_name.replace(".", "-"), Path("/tmp") / module_name.replace(".", "-"))
        server.module = module
        try:
            configure = getattr(module, "configure", None)
            if callable(configure):
                try:
                    configure(server, False)
                except ValueError as exc:
                    if str(exc) != "No Port":
                        raise
                    configure(server, False, port=_default_test_port(module_name))
            _seed_install_state(server)
            runtime_module.ensure_runtime_hooks(module)
            requirements = runtime_module._get_module_hook(module, "get_runtime_requirements")(server)
            spec = runtime_module._get_module_hook(module, "get_container_spec")(server)

            family = runtime_module.canonicalize_runtime_family(requirements.get("family"))
            if requirements.get("engine") != "docker":
                offenders.append(module_name + ": runtime engine is not docker")
                continue
            if family not in runtime_module.RUNTIME_FAMILY_DEFAULTS:
                offenders.append(module_name + ": unknown runtime family %r" % (family,))
                continue
            if "dir" in server.data and not requirements.get("mounts"):
                offenders.append(module_name + ": missing Docker mounts")
                continue
            if not isinstance(spec.get("command"), list) or not spec.get("command"):
                offenders.append(module_name + ": missing Docker command")
                continue
            if spec.get("working_dir") is None:
                offenders.append(module_name + ": missing working_dir")
                continue
        finally:
            for attribute_name, original in original_resolvers.items():
                setattr(module, attribute_name, original)

    assert offenders == []
