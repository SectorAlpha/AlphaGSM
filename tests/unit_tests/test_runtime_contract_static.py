"""Static contract tests for Docker runtime metadata coverage."""

# pylint: disable=protected-access

import os
import shutil
from pathlib import Path

from server import ServerError
from server.module_catalog import load_default_module_catalog
from server.module_parity import _module_source_path
from importlib import import_module
import server.runtime as runtime_module

GAME_CONFIG_HINTS = {
    '"port"',
    '"queryport"',
    '"maxplayers"',
    '"servername"',
    '"hostname"',
    '"map"',
    '"scenarioid"',
    '"gamemode"',
    '"difficulty"',
    '"levelname"',
}
DEFAULT_TEST_WORK_DIR = Path("/tmp/alphagsm-work")


def _game_module_names():
    catalog = load_default_module_catalog()
    return list(catalog.canonical_modules)


def test_game_module_inventory_excludes_catalog_alias_keys():
    module_names = _game_module_names()

    assert "tf2" not in module_names
    assert "tf2server" not in module_names
    assert "tf2c" not in module_names
    assert "tf2classifiedserver" not in module_names
    assert "cs2server" not in module_names
    assert "minecraft.DEFAULT" not in module_names


def test_game_module_inventory_counts_teamfortress2_once():
    module_names = _game_module_names()

    assert module_names.count("teamfortress2") == 1


def _module_source(module_name):
    """Return the source text for a game module.

    For package-backed modules, concatenate all .py files in the package so
    contract checks see the full implementation surface, not just __init__.py.
    """

    source_path = _module_source_path(Path("."), module_name)
    if source_path.name == "__init__.py":
        parts = [
            p.read_text(encoding="utf-8")
            for p in sorted(source_path.parent.rglob("*.py"))
        ]
        return "\n".join(parts)
    return source_path.read_text(encoding="utf-8")


def _runtime_contract_root(module_name):
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    if work_dir:
        root = Path(work_dir).expanduser() / "pytest-runtime-contract" / module_name.replace(".", "-")
    else:
        root = DEFAULT_TEST_WORK_DIR / "pytest-runtime-contract" / module_name.replace(".", "-")
    shutil.rmtree(root, ignore_errors=True)
    return root


class _DataStore(dict):
    def save(self):
        return None


class _FakeServer:
    def __init__(self, name, base_dir):
        self.name = name
        self.data = _DataStore(dir=str(base_dir / "server") + "/")
        self.module = None


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

    targets = [module]
    try:
        main_module = import_module(module.__name__ + ".main")
    except ImportError:
        main_module = None
    if main_module is not None and main_module is not module:
        targets.append(main_module)
    if module_name in ("minecraft.velocity", "minecraft.waterfall"):
        targets.append(import_module("gamemodules.minecraft.bungeecord"))

    for target in targets:
        for attribute_name in dir(target):
            original = getattr(target, attribute_name, None)
            if not callable(original):
                continue
            if (
                ("resolve" not in attribute_name or "download" not in attribute_name)
                and "file_url" not in attribute_name
            ):
                continue
            originals[(target, attribute_name)] = original
            if "file_url" in attribute_name:
                setattr(
                    target,
                    attribute_name,
                    lambda *args, **kwargs: "https://example.invalid/%s.zip"
                    % (module_name.replace(".", "-"),),
                )
                continue
            setattr(target, attribute_name, _fake_resolve_download)

    return originals


def _seed_install_state(server):
    next_port = 27015
    for key, value in list(server.data.items()):
        if not str(key).lower().endswith("port"):
            continue
        try:
            port = int(value)
        except (TypeError, ValueError):
            continue
        if port > 0:
            continue
        server.data[key] = next_port
        next_port += 1

    root = Path(server.data["dir"])
    root.mkdir(parents=True, exist_ok=True)

    xnt_launcher = root / "server" / "server_linux.sh"
    xnt_launcher.parent.mkdir(parents=True, exist_ok=True)
    if not xnt_launcher.exists():
        xnt_launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(xnt_launcher, 0o755)

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
        if (
            "def get_runtime_requirements(" not in source
            and "get_runtime_requirements = " not in source
        ):
            offenders.append(module_name + ": missing get_runtime_requirements")
        if "def get_container_spec(" not in source and "get_container_spec = " not in source:
            offenders.append(module_name + ": missing get_container_spec")
    assert offenders == []


def test_all_game_modules_resolve_valid_docker_manifests():
    offenders = []
    for module_name in _game_module_names():
        module = import_module("gamemodules." + module_name)
        original_resolvers = _stub_download_resolution(module, module_name)
        server_root = _runtime_contract_root(module_name)
        server = _FakeServer("it-" + module_name.replace(".", "-"), server_root)
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
            try:
                spec = runtime_module._get_module_hook(module, "get_container_spec")(server)
            except ServerError as exc:
                if str(exc).startswith("ENABLED (BYO):") or str(exc).startswith("ENABLED (AUTH):"):
                    continue
                raise
            if not isinstance(spec.get("command"), list) or not spec.get("command"):
                offenders.append(module_name + ": missing Docker command")
                continue
            if spec.get("working_dir") is None:
                offenders.append(module_name + ": missing working_dir")
                continue
        finally:
            for (target, attribute_name), original in original_resolvers.items():
                setattr(target, attribute_name, original)
            shutil.rmtree(server_root, ignore_errors=True)

    if offenders:
        raise AssertionError(offenders)


def test_docker_runtime_commands_do_not_embed_the_host_install_dir():
    import utils.proton as proton_module

    offenders = []
    original_find_proton = proton_module.find_proton
    original_find_wine = proton_module.find_wine
    proton_module.find_proton = lambda: "/usr/bin/proton"
    proton_module.find_wine = lambda: None
    try:
        for module_name in _game_module_names():
            module = import_module("gamemodules." + module_name)
            original_resolvers = _stub_download_resolution(module, module_name)
            server_root = _runtime_contract_root(module_name)
            server = _FakeServer("it-" + module_name.replace(".", "-"), server_root)
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
                if requirements.get("engine") != "docker":
                    continue
                server.data["runtime"] = "docker"
                try:
                    command, _cwd = runtime_module._get_module_hook(module, "get_start_command")(server)
                except ServerError as exc:
                    if str(exc).startswith("ENABLED (BYO):") or str(exc).startswith("ENABLED (AUTH):"):
                        continue
                    raise
                install_dir = server.data.get("dir")
                if install_dir and any(
                    isinstance(arg, str) and (arg == install_dir or arg.startswith(install_dir))
                    for arg in command
                ):
                    offenders.append(module_name + ": embedded host install dir in Docker command")
            finally:
                for (target, attribute_name), original in original_resolvers.items():
                    setattr(target, attribute_name, original)
                shutil.rmtree(server_root, ignore_errors=True)
    finally:
        proton_module.find_proton = original_find_proton
        proton_module.find_wine = original_find_wine

    if offenders:
        raise AssertionError(offenders)


def test_modules_using_xvfb_run_declare_the_host_dependency():
    offenders = []
    for module_name in _game_module_names():
        source = _module_source(module_name)
        if "xvfb-run" not in source:
            continue

        module = import_module("gamemodules." + module_name)
        original_resolvers = _stub_download_resolution(module, module_name)
        server_root = _runtime_contract_root(module_name)
        server = _FakeServer("it-" + module_name.replace(".", "-"), server_root)
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
            dependency_ids = {item["id"] for item in requirements.get("host_dependencies", [])}
            if "xvfb-run" not in dependency_ids:
                offenders.append(module_name + ": missing xvfb-run host dependency metadata")
        finally:
            for (target, attribute_name), original in original_resolvers.items():
                setattr(target, attribute_name, original)
            shutil.rmtree(server_root, ignore_errors=True)

    assert offenders == []


def test_modules_with_explicit_7z_prereq_declare_the_host_dependency():
    offenders = []
    for module_name in _game_module_names():
        source = _module_source(module_name)
        if "7z-compatible extractor" not in source:
            continue

        module = import_module("gamemodules." + module_name)
        original_resolvers = _stub_download_resolution(module, module_name)
        server_root = _runtime_contract_root(module_name)
        server = _FakeServer("it-" + module_name.replace(".", "-"), server_root)
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
            dependency_ids = {item["id"] for item in requirements.get("host_dependencies", [])}
            if "7z" not in dependency_ids:
                offenders.append(module_name + ": missing 7z host dependency metadata")
        finally:
            for (target, attribute_name), original in original_resolvers.items():
                setattr(target, attribute_name, original)
            shutil.rmtree(server_root, ignore_errors=True)

    assert offenders == []


def test_managed_config_modules_declare_config_sync_contract():
    offenders = []
    for module_name in _game_module_names():
        source = _module_source(module_name)
        has_sync_function = "def sync_server_config(" in source
        has_config_sync_keys = "config_sync_keys" in source or "set_sync_keys" in source

        if has_sync_function and not has_config_sync_keys:
            offenders.append(module_name + ": missing config_sync_keys for sync_server_config")
            continue

        manages_real_config = (
            'setdefault("configfile"' in source
            and "def checkvalue(" in source
            and any(hint in source for hint in GAME_CONFIG_HINTS)
            and (
                "updateconfig(" in source
                or "json.dump(" in source
                or "xml.etree" in source
                or "ElementTree" in source
                or "server.json" in source
            )
        )

        if manages_real_config and not has_config_sync_keys:
            offenders.append(module_name + ": manages real server config but missing config_sync_keys")

    assert offenders == []
