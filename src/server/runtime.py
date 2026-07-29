"""Runtime abstraction for AlphaGSM server execution.

Supports the existing process-backed runtime and an additional Docker-backed
container runtime. Game modules can describe Docker requirements via
``get_runtime_requirements(server)`` and ``get_container_spec(server)`` hooks,
but Docker is only selected when configuration opts into it.
"""

# pylint: disable=too-many-lines

from __future__ import annotations

import copy
import contextvars
import ctypes
import ipaddress
import json
import os
import posixpath
import re
import shlex
import shutil
import socket
import stat
import subprocess as sp
import sys

from server import ServerError
import screen
from utils.settings import settings
from utils.gamemodules import common as gamemodule_common
from utils import proton
from utils import steamcmd as steamcmd_module
from utils.platform_info import PLATFORM


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_IMAGE_REGISTRY = "ghcr.io/sectoralpha"
DEFAULT_IMAGE_TAG = "latest"
JAVA_VERSION_RE = re.compile(r'version\s+"(\d+)(?:\.(\d+))?')
PLATFORM_DISPLAY_NAMES = {
    "linux": "Linux",
    "windows": "Windows",
    "macos": "macOS",
}


def default_runtime_image(family):
    """Return the default GHCR image reference for a runtime family."""

    family = str(family).strip().lower()
    return f"{DEFAULT_IMAGE_REGISTRY}/alphagsm-{family}-runtime:{DEFAULT_IMAGE_TAG}"


class RuntimeError(Exception):
    """Raised when runtime selection or control fails."""


RUNTIME_DATA_KEYS = (
    "runtime",
    "runtime_family",
    "image",
    "java_major",
    "container_name",
    "mounts",
    "env",
    "ports",
    "network_mode",
    "stop_mode",
)

RUNTIME_FAMILY_ALIASES = {
    "minecraft": "java",
    "ts3": "service-console",
}

RUNTIME_FAMILY_DEFAULTS = {
    "java": {
        "runtime": "docker",
        "runtime_family": "java",
        "image": default_runtime_image("java"),
        "network_mode": "bridge",
        "stop_mode": "docker-stop",
        "java_major": 17,
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "quake-linux": {
        "runtime": "docker",
        "runtime_family": "quake-linux",
        "image": default_runtime_image("quake-linux"),
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "service-console": {
        "runtime": "docker",
        "runtime_family": "service-console",
        "image": default_runtime_image("service-console"),
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "simple-tcp": {
        "runtime": "docker",
        "runtime_family": "simple-tcp",
        "image": default_runtime_image("simple-tcp"),
        "network_mode": "bridge",
        "stop_mode": "docker-stop",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "steamcmd-linux": {
        "runtime": "docker",
        "runtime_family": "steamcmd-linux",
        "image": default_runtime_image("steamcmd-linux"),
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "wine-proton": {
        "runtime": "docker",
        "runtime_family": "wine-proton",
        "image": default_runtime_image("wine-proton"),
        "network_mode": "bridge",
        "stop_mode": "docker-stop",
        "env": {},
        "mounts": [],
        "ports": [],
    },
}

VALID_RUNTIME_BACKENDS = ("process", "docker")
VALID_STOP_MODES = ("docker-stop", "exec-console")
DEFAULT_CONTAINER_WORKDIR = "/srv/server"
DEFAULT_HOST_USER_CONTAINER_HOME = "/home/alphagsm"
RUNTIME_STATE_DIRECTORY_NAME = "runtime"
RUNTIME_FAMILY_DOCKERFILES = {
    "java": os.path.join("docker", "java", "Dockerfile"),
    "quake-linux": os.path.join("docker", "quake-linux", "Dockerfile"),
    "service-console": os.path.join("docker", "service-console", "Dockerfile"),
    "simple-tcp": os.path.join("docker", "simple-tcp", "Dockerfile"),
    "steamcmd-linux": os.path.join("docker", "steamcmd-linux", "Dockerfile"),
    "wine-proton": os.path.join("docker", "wine-proton", "Dockerfile"),
}


def canonicalize_runtime_family(family):
    """Return the canonical runtime family name for *family*."""

    if family is None:
        return None
    family = str(family).strip().lower()
    return RUNTIME_FAMILY_ALIASES.get(family, family)


def _process_host_checks_supported():
    """Return whether local process-runtime dependency checks should run."""

    return _current_host_platform() in {"linux", "windows", "macos"}


def _current_host_platform():
    """Return the normalized host platform name."""

    return PLATFORM


def _current_host_platform_display_name():
    """Return the display name for the current host platform."""

    return PLATFORM_DISPLAY_NAMES.get(_current_host_platform(), _current_host_platform())


def _get_module_hook(module, hook_name):
    """Return a callable hook from a module or its shared ``MODULE`` surface."""

    for owner in (module, getattr(module, "MODULE", None)):
        hook = getattr(owner, hook_name, None)
        if callable(hook):
            return hook
    return None


def _has_explicit_module_hook(module, hook_name):
    """Return whether *module* or its shared MODULE surface defines *hook_name*."""

    for owner in (module, getattr(module, "MODULE", None)):
        if owner is not None and hook_name in getattr(owner, "__dict__", {}):
            return True
    return False


def _safe_protocol_hint(server, module):
    """Best-effort query/info protocol hint for runtime family inference."""

    for hook_name in ("get_query_address", "get_info_address"):
        hook = _get_module_hook(module, hook_name)
        if hook is None:
            continue
        try:
            address = hook(server)
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            continue
        if isinstance(address, (list, tuple)) and len(address) >= 3:
            protocol = str(address[2]).strip().lower()
            if protocol:
                return protocol
    return None


def _infer_runtime_family(server, module):
    """Infer a Docker runtime family for a module without explicit hooks."""

    module_name = str(getattr(module, "__name__", "")).lower()
    exe_name = os.path.basename(str(server.data.get("exe_name", ""))).lower()
    protocol = _safe_protocol_hint(server, module)

    if server.data.get("wineprefix") or exe_name.endswith(".exe"):
        return "wine-proton"
    if exe_name.endswith(".jar") or module_name.startswith("gamemodules.minecraft."):
        return "java"
    if "ts3" in module_name or exe_name.startswith("ts3server"):
        return "service-console"
    if protocol == "quake":
        return "quake-linux"
    if protocol == "ts3":
        return "service-console"
    return "steamcmd-linux"


def _infer_port_definitions(server, family=None):
    """Infer Docker port definitions from common server datastore keys."""

    family = canonicalize_runtime_family(family)
    definitions = []
    seen = set()
    for key, value in server.data.items():
        lower_key = str(key).lower()
        if not (lower_key == "port" or lower_key.endswith("port")):
            continue
        try:
            int(value)
        except (TypeError, ValueError):
            continue

        if family == "java":
            protocols = ("tcp",)
        elif family == "service-console":
            if lower_key == "port":
                protocols = ("udp",)
            else:
                protocols = ("tcp",)
        elif lower_key in ("clientport", "sourcetvport", "steamport"):
            protocols = ("udp",)
        elif lower_key.startswith("rmi") or "http" in lower_key or "web" in lower_key:
            protocols = ("tcp",)
        elif lower_key.endswith("queryport"):
            protocols = ("udp", "tcp")
        elif family == "wine-proton":
            protocols = ("udp", "tcp")
        else:
            protocols = ("udp", "tcp")

        for protocol in protocols:
            definition = (lower_key, protocol)
            if definition in seen:
                continue
            seen.add(definition)
            definitions.append({"key": key, "protocol": protocol})
    return definitions


def infer_port_definitions(server, family=None):
    """Return the inferred Docker port definitions for *server*."""

    return _infer_port_definitions(server, family)


def build_port_specs(server, port_definitions):
    """Return normalized port mappings for the requested server data keys."""

    ports = []
    for definition in port_definitions or ():
        if isinstance(definition, dict):
            key = definition.get("key")
            if key not in server.data or server.data[key] is None:
                continue
            base_port = int(server.data[key])
            offset = int(definition.get("offset", 0))
            host_port = base_port + offset
            container_port = int(definition.get("container", host_port))
            for label, port in (("host", host_port), ("container", container_port)):
                if port < 1 or port > 65535:
                    raise RuntimeError(
                        "Invalid {} port {} derived from {} for server {}".format(
                            label,
                            port,
                            key,
                            getattr(server, "name", "<unknown>"),
                        )
                    )
            ports.append(
                {
                    "host": host_port,
                    "container": container_port,
                    "protocol": definition.get("protocol", "udp"),
                }
            )
            continue
        if isinstance(definition, tuple):
            key, protocol = definition
        else:
            key, protocol = definition, "udp"
        if key not in server.data or server.data[key] is None:
            continue
        ports.append(
            {
                "host": int(server.data[key]),
                "container": int(server.data[key]),
                "protocol": protocol,
            }
        )
    return ports


def _normalize_container_home(container_home):
    """Return a safe absolute Docker home path."""

    container_home = str(container_home or "").strip()
    normalized = posixpath.normpath(container_home)
    if (
        not container_home
        or not container_home.startswith("/")
        or normalized == "/"
        or ":" in container_home
    ):
        raise RuntimeError(
            "container_home must be an absolute container path below /"
        )
    return normalized


def _configured_manager_root():
    """Return the stable manager-owned root without inspecting Docker."""

    shared_root = os.environ.get("ALPHAGSM_HOME", "").strip()
    if shared_root:
        return os.path.abspath(os.path.expanduser(shared_root))

    config_location = os.environ.get("ALPHAGSM_CONFIG_LOCATION", "").strip()
    if config_location:
        return os.path.dirname(
            os.path.abspath(os.path.expanduser(config_location))
        )

    alphagsm_path = os.path.abspath(
        os.path.expanduser(
            settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm")
        )
    )
    if os.path.basename(alphagsm_path.rstrip(os.sep)) == "home":
        return os.path.dirname(alphagsm_path)
    return alphagsm_path


def _server_runtime_home_source(server):
    """Return the manager-owned per-server host path for container HOME."""

    server_name = str(getattr(server, "name", "")).strip()
    if (
        not server_name
        or server_name in (".", "..")
        or os.path.basename(server_name) != server_name
        or (os.path.altsep and os.path.altsep in server_name)
    ):
        raise RuntimeError("Invalid server name for runtime state: " + server_name)
    return os.path.join(
        _configured_manager_root(),
        RUNTIME_STATE_DIRECTORY_NAME,
        server_name,
        "home",
    )


def _normalize_mount_mode(mode, *, read_only=False):
    """Return a canonical Docker bind-mount mode token list."""

    if mode is None:
        tokens = []
    elif isinstance(mode, (list, tuple)):
        tokens = [str(token).strip() for token in mode]
    else:
        tokens = [token.strip() for token in str(mode).split(",")]
    tokens = [token for token in tokens if token]
    access_tokens = {token.lower() for token in tokens if token.lower() in ("ro", "rw")}
    if read_only:
        access_tokens.add("ro")
        tokens = [token for token in tokens if token.lower() != "rw"]
        if not any(token.lower() == "ro" for token in tokens):
            tokens.insert(0, "ro")
    if access_tokens == {"ro", "rw"}:
        raise RuntimeError("Mount mode cannot contain both ro and rw")
    if not tokens:
        tokens = ["rw"]
    return ",".join(tokens)


def _normalize_mount(mount):
    """Return one canonical bind-mount mapping."""

    if isinstance(mount, dict):
        source = mount.get("source", mount.get("src"))
        target = mount.get(
            "target", mount.get("destination", mount.get("dst"))
        )
        mode = _normalize_mount_mode(
            mount.get("mode"), read_only=bool(mount.get("read_only", False))
        )
    elif isinstance(mount, str):
        parts = mount.rsplit(":", 2)
        if len(parts) == 2:
            source, target = parts
            mode = "rw"
        elif len(parts) == 3:
            source, target, mode = parts
            if mode.startswith("/"):
                source = source + ":" + target
                target = mode
                mode = "rw"
            mode = _normalize_mount_mode(mode)
        else:
            raise RuntimeError("Invalid bind mount: " + mount)
    else:
        raise RuntimeError("Invalid bind mount declaration")

    source = str(source or "").strip()
    target = str(target or "").strip()
    if not source or not target:
        raise RuntimeError("Bind mounts require both source and target paths")
    if not target.startswith("/") or ":" in target:
        raise RuntimeError("Container mount target must be an absolute path: " + target)
    return {
        "source": source,
        "target": posixpath.normpath(target),
        "mode": mode,
    }


def _normalize_mounts(mounts):
    """Normalize mounts and reject duplicate canonical container targets."""

    normalized_mounts = []
    targets = set()
    for mount in mounts or ():
        normalized = _normalize_mount(mount)
        target = normalized["target"]
        if target in targets:
            raise RuntimeError("Duplicate container mount target: " + target)
        targets.add(target)
        normalized_mounts.append(normalized)
    return normalized_mounts


def _mount_target(mount):
    """Return the container target from a normalized or string mount spec."""

    if isinstance(mount, dict):
        return mount.get("target", mount.get("destination", mount.get("dst")))
    return _normalize_mount(mount)["target"]


def _mount_source(mount):
    """Return the host source from a normalized or string mount spec."""

    if isinstance(mount, dict):
        return mount.get("source", mount.get("src"))
    return _normalize_mount(mount)["source"]


def _mount_mode(mount):
    """Return the access mode from a normalized or string mount spec."""

    if isinstance(mount, dict):
        return _normalize_mount_mode(
            mount.get("mode"), read_only=bool(mount.get("read_only", False))
        )
    return _normalize_mount(mount)["mode"]


def _mount_is_read_only(mount):
    """Return whether a normalized mount mode contains the ``ro`` token."""

    return "ro" in {
        token.strip().lower() for token in _mount_mode(mount).split(",")
    }


def _steamcmd_sdk_mounts(container_home="/root"):
    """Return Docker mounts for SteamCMD's SDK and canonical client paths."""

    mounts = []
    for src_subdir, target_dirs in (
        (
            "linux64",
            (
                posixpath.join(container_home, ".steam", "sdk64"),
                posixpath.join(container_home, ".steam", "steamcmd", "linux64"),
            ),
        ),
        (
            "linux32",
            (
                posixpath.join(container_home, ".steam", "sdk32"),
                posixpath.join(container_home, ".steam", "steamcmd", "linux32"),
            ),
        ),
    ):
        source_dir = os.path.join(steamcmd_module.STEAMCMD_DIR, src_subdir)
        source_file = os.path.join(source_dir, "steamclient.so")
        if not os.path.isfile(source_file):
            continue
        mounts.extend(
            {"source": source_dir, "target": target_dir, "mode": "ro"}
            for target_dir in target_dirs
        )
    return mounts


def build_runtime_requirements(
    server,
    *,
    family,
    port_definitions=(),
    env=None,
    mounts=None,
    extra=None,
):
    """Build a normalized Docker runtime-requirements mapping."""

    family = canonicalize_runtime_family(family)
    resolved_env = dict(env or {})
    resolved_extra = copy.deepcopy(dict(extra or {}))
    run_as_host_user = bool(resolved_extra.get("run_as_host_user", False))
    container_home = None
    if run_as_host_user:
        container_home = _normalize_container_home(
            resolved_env.get("HOME")
            or resolved_extra.get("container_home")
            or DEFAULT_HOST_USER_CONTAINER_HOME
        )
        resolved_env.setdefault("HOME", container_home)
        resolved_extra["run_as_host_user"] = True
        resolved_extra["container_home"] = container_home

    requirements = {
        "engine": "docker",
        "family": family,
    }
    resolved_mounts = list(mounts or ())
    if mounts is None and "dir" in server.data:
        resolved_mounts = [
            {
                "source": server.data["dir"],
                "target": DEFAULT_CONTAINER_WORKDIR,
                "mode": "rw",
            }
        ]
    if run_as_host_user and not any(
        posixpath.normpath(str(_mount_target(mount))) == container_home
        for mount in resolved_mounts
    ):
        resolved_mounts.append(
            {
                "source": _server_runtime_home_source(server),
                "target": container_home,
                "mode": "rw",
            }
        )
    if mounts is None and "dir" in server.data and family == "steamcmd-linux":
        if run_as_host_user:
            resolved_mounts.extend(_steamcmd_sdk_mounts(container_home))
        else:
            resolved_mounts.extend(_steamcmd_sdk_mounts())
    if resolved_mounts:
        requirements["mounts"] = _normalize_mounts(resolved_mounts)
    ports = build_port_specs(server, port_definitions)
    if ports:
        requirements["ports"] = ports
    if resolved_env:
        requirements["env"] = resolved_env
    if resolved_extra:
        requirements.update(resolved_extra)
    return requirements


def _normalize_host_dependency_spec(spec, server_name):
    """Return a normalized host-dependency mapping."""

    if isinstance(spec, str):
        spec = {"id": spec, "command": spec}
    elif not isinstance(spec, dict):
        raise RuntimeError(
            "Invalid host dependency declaration for server %s" % (server_name,)
        )

    normalized = dict(spec)
    if "binary" in normalized and "command" not in normalized:
        normalized["command"] = normalized.pop("binary")

    dep_id = str(
        normalized.get("id")
        or normalized.get("name")
        or normalized.get("command")
        or ""
    ).strip().lower()
    if not dep_id:
        raise RuntimeError(
            "Host dependency declarations must include an id or command for server %s"
            % (server_name,)
        )

    normalized["id"] = dep_id
    if "display_name" not in normalized:
        normalized["display_name"] = normalized.get("name") or dep_id
    if "library" in normalized and "library_names" not in normalized:
        normalized["library_names"] = normalized.pop("library")

    if "install_hint" in normalized and "install_hints" not in normalized:
        normalized["install_hints"] = normalized.pop("install_hint")

    platforms = normalized.get("platforms")
    if platforms not in (None, ""):
        if isinstance(platforms, str):
            platforms = [platforms]
        elif not isinstance(platforms, (list, tuple, set)):
            raise RuntimeError(
                "Host dependency '%s' has invalid platforms for server %s"
                % (dep_id, server_name)
            )
        normalized["platforms"] = [
            str(platform).strip().lower()
            for platform in list(platforms)
            if str(platform).strip()
        ]

    default_kind = "shared-library" if "library_names" in normalized else dep_id if dep_id == "java" else "command"
    normalized["kind"] = str(
        normalized.get("kind") or default_kind
    ).strip().lower().replace("_", "-")

    if "command_key" in normalized and normalized["command_key"] not in (None, ""):
        normalized["command_key"] = str(normalized["command_key"]).strip()

    command = normalized.get("command")
    if command in (None, "") and "command_key" not in normalized:
        command = dep_id
    if command not in (None, ""):
        if isinstance(command, (list, tuple)):
            if command and isinstance(command[0], (list, tuple, dict)):
                normalized["command"] = [
                    [str(part) for part in variant]
                    if isinstance(variant, (list, tuple))
                    else dict(variant) if isinstance(variant, dict)
                    else str(variant)
                    for variant in command
                ]
            else:
                normalized["command"] = [str(part) for part in command]
        else:
            normalized["command"] = str(command).strip()

    minimum_major = normalized.get("minimum_major")
    if minimum_major not in (None, ""):
        normalized["minimum_major"] = int(minimum_major)

    library_names = normalized.get("library_names")
    if library_names not in (None, ""):
        if isinstance(library_names, str):
            library_names = {"default": library_names}
        elif not isinstance(library_names, dict):
            raise RuntimeError(
                "Host dependency '%s' has invalid library_names for server %s"
                % (dep_id, server_name)
            )
        normalized["library_names"] = {
            str(key).strip().lower(): str(value).strip()
            for key, value in dict(library_names).items()
            if str(key).strip() and str(value).strip()
        }

    install_hints = normalized.get("install_hints")
    if install_hints not in (None, ""):
        if isinstance(install_hints, str):
            install_hints = {"default": install_hints}
        elif not isinstance(install_hints, dict):
            raise RuntimeError(
                "Host dependency '%s' has invalid install_hints for server %s"
                % (dep_id, server_name)
            )
        normalized["install_hints"] = {
            str(key).strip().lower(): str(value).strip()
            for key, value in dict(install_hints).items()
            if str(key).strip() and str(value).strip()
        }

    return normalized


def _normalize_host_dependency_specs(specs, server_name):
    """Return normalized host dependencies for *specs*."""

    if specs in (None, ""):
        return []
    if isinstance(specs, (str, dict)):
        specs = [specs]
    return [
        _normalize_host_dependency_spec(spec, server_name)
        for spec in list(specs)
    ]


def _command_argv(command):
    """Return an argv list for *command*."""

    if isinstance(command, (list, tuple)):
        return [str(part) for part in command if str(part).strip()]
    command = str(command or "").strip()
    if not command:
        return []
    return shlex.split(command)


def _resolve_host_dependency_variants(spec, server):
    """Return candidate command variants for a dependency spec."""

    command = None
    command_key = spec.get("command_key")
    if command_key:
        command = server.data.get(command_key)
    if command in (None, ""):
        command = spec.get("command")

    if isinstance(command, (list, tuple)) and command and isinstance(command[0], (list, tuple, dict)):
        raw_variants = list(command)
    else:
        raw_variants = [command]

    variants = []
    for raw_variant in raw_variants:
        variant_spec = raw_variant
        if isinstance(raw_variant, dict):
            variant_spec = raw_variant.get("command")
        argv = _command_argv(variant_spec)
        if argv:
            variants.append(
                {
                    "label": raw_variant.get("label") if isinstance(raw_variant, dict) else None,
                    "argv": argv,
                }
            )
    if not variants:
        raise RuntimeError(
            "Host dependency '%s' does not define a command to check"
            % (spec.get("id", "dependency"),)
        )
    return variants


def _resolve_host_dependency_library_name(spec):
    """Return the platform-appropriate shared-library name for *spec*."""

    library_names = dict(spec.get("library_names") or {})
    platform_name = _current_host_platform()
    library_name = library_names.get(platform_name) or library_names.get("default")
    if library_name:
        return library_name
    raise RuntimeError(
        "Host dependency '%s' does not define a shared library for %s"
        % (spec.get("id", "dependency"), platform_name)
    )


def _host_dependency_applies_to_current_platform(spec):
    """Return whether *spec* applies to the current host platform."""

    platforms = list(spec.get("platforms") or ())
    if not platforms:
        return True
    return _current_host_platform() in platforms


def _resolve_host_dependency_install_hint(spec, entry):
    """Return a platform-aware install hint for a failed dependency."""

    platform_name = _current_host_platform()
    display_platform = _current_host_platform_display_name()
    install_hints = dict(spec.get("install_hints") or {})
    if install_hints:
        hint = install_hints.get(platform_name) or install_hints.get("default")
        if hint:
            return hint

    if entry.get("kind") == "java":
        minimum_major = entry.get("minimum_major")
        if minimum_major not in (None, ""):
            return f"Install Java {minimum_major}+ on this {display_platform} host before launching the server locally."
        return f"Install Java on this {display_platform} host before launching the server locally."

    if entry.get("kind") == "shared-library":
        library_name = entry.get("library_name")
        if library_name:
            return (
                f"Install the host runtime that provides '{library_name}' on this "
                f"{display_platform} host before launching the server locally."
            )

    return (
        f"Install {entry.get('display_name', 'the required dependency')} on this "
        f"{display_platform} host before launching the server locally."
    )


def _format_command(argv):
    """Return a shell-style string for *argv*."""

    return " ".join(shlex.quote(str(part)) for part in argv)


def _find_command_path(executable):
    """Return the resolved path for *executable* when it exists."""

    executable = str(executable or "").strip()
    if not executable:
        return None
    if os.path.isabs(executable) or os.sep in executable:
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            return executable
        return None
    return shutil.which(executable)


def _read_java_major(command_argv):
    """Return the detected Java major version for *command_argv*."""

    try:
        result = sp.run(
            list(command_argv) + ["-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, sp.SubprocessError):
        return None

    output = "\n".join(filter(None, [result.stdout, result.stderr]))
    match = JAVA_VERSION_RE.search(output)
    if not match:
        return None
    major = int(match.group(1))
    if major == 1 and match.group(2):
        return int(match.group(2))
    return major


def _infer_process_host_dependencies(server, requirements):
    """Infer Linux process-runtime host dependencies for *server*."""

    dependencies = []
    family = canonicalize_runtime_family(requirements.get("runtime_family"))
    java_major = requirements.get("java_major")
    exe_name = os.path.basename(str(server.data.get("exe_name", ""))).lower()

    if family == "java" or java_major is not None or exe_name.endswith(".jar"):
        spec = {
            "id": "java",
            "display_name": "Java",
            "kind": "java",
            "command_key": "javapath",
            "command": "java",
        }
        if java_major not in (None, ""):
            try:
                spec["minimum_major"] = int(java_major)
            except (TypeError, ValueError):
                pass
        dependencies.append(spec)

    return dependencies


def get_process_host_dependency_report(server):
    """Return process-runtime dependency status for *server*."""

    report = {
        "applicable": False,
        "ok": True,
        "requirements": [],
    }

    if not _process_host_checks_supported():
        report["skipped_reason"] = "host dependency checks only run on Linux"
        return report

    metadata = resolve_runtime_metadata(server)
    runtime_name = metadata.get("runtime", "process")
    if runtime_name == "docker":
        report["skipped_reason"] = "docker runtime supplies its own dependencies"
        return report

    report["applicable"] = True
    module = getattr(server, "module", None)
    requirements = _get_module_runtime_requirements(server)
    if not requirements:
        requirements = normalize_runtime_requirements(
            infer_runtime_requirements(server, module=module),
            server.name,
        )

    explicit_dependencies = list(requirements.get("host_dependencies") or ())
    dependency_specs = []
    seen_ids = set()
    for spec in explicit_dependencies + _infer_process_host_dependencies(server, requirements):
        dep_id = spec.get("id")
        if dep_id in seen_ids:
            continue
        seen_ids.add(dep_id)
        dependency_specs.append(spec)

    for spec in dependency_specs:
        if not _host_dependency_applies_to_current_platform(spec):
            continue
        entry = {
            "id": spec["id"],
            "display_name": spec.get("display_name", spec["id"]),
            "kind": spec.get("kind", "command"),
            "ok": True,
        }
        if entry["kind"] == "shared-library":
            try:
                library_name = _resolve_host_dependency_library_name(spec)
            except RuntimeError as ex:
                entry["ok"] = False
                entry["error"] = str(ex)
                report["requirements"].append(entry)
                continue

            entry["library_name"] = library_name
            try:
                ctypes.CDLL(library_name)
            except OSError as ex:
                entry["ok"] = False
                entry["error"] = (
                    "%s is required but shared library '%s' could not be loaded: %s"
                    % (entry["display_name"], library_name, str(ex))
                )
        else:
            try:
                variants = _resolve_host_dependency_variants(spec, server)
            except RuntimeError as ex:
                entry["ok"] = False
                entry["error"] = str(ex)
                report["requirements"].append(entry)
                continue

            missing_commands = []
            for variant in variants:
                argv = variant["argv"]
                resolved_path = _find_command_path(argv[0])
                if resolved_path is None:
                    missing_commands.append(argv[0])
                    continue

                entry["command"] = _format_command(argv)
                entry["resolved_path"] = resolved_path
                if variant.get("label"):
                    entry["matched_variant"] = variant["label"]

                if entry["kind"] == "java":
                    installed_major = _read_java_major(argv)
                    if installed_major is None:
                        entry["ok"] = False
                        entry["error"] = (
                            "Unable to determine the installed Java version from %s"
                            % (_format_command(list(argv) + ["-version"]),)
                        )
                    else:
                        entry["installed_major"] = installed_major
                        minimum_major = spec.get("minimum_major")
                        if minimum_major not in (None, ""):
                            entry["minimum_major"] = int(minimum_major)
                            if installed_major < int(minimum_major):
                                entry["ok"] = False
                                entry["error"] = (
                                    "%s %s+ is required but %s is installed"
                                    % (
                                        entry["display_name"],
                                        int(minimum_major),
                                        installed_major,
                                    )
                                )
                break
            else:
                entry["ok"] = False
                unique_commands = []
                for command_name in missing_commands:
                    if command_name not in unique_commands:
                        unique_commands.append(command_name)
                if len(unique_commands) == 1:
                    entry["error"] = (
                        "%s is required but command '%s' was not found"
                        % (entry["display_name"], unique_commands[0])
                    )
                else:
                    entry["error"] = (
                        "%s is required but none of these commands were found: %s"
                        % (entry["display_name"], ", ".join("'" + item + "'" for item in unique_commands))
                    )

        if not entry.get("ok", False):
            entry["install_hint"] = _resolve_host_dependency_install_hint(spec, entry)

        report["requirements"].append(entry)

    report["ok"] = all(item.get("ok", False) for item in report["requirements"])
    return report


def assert_host_install_requirements(server, phase="run"):
    """Raise when process-runtime host dependencies are missing."""

    report = get_process_host_dependency_report(server)
    if not report.get("applicable") or report.get("ok", True):
        return report

    failures = []
    for item in report.get("requirements", []):
        if item.get("ok", False):
            continue
        failure = item["error"]
        install_hint = item.get("install_hint")
        if install_hint:
            failure += " " + install_hint
        failures.append(failure)
    action = str(phase or "run")
    raise RuntimeError(
        "Can't %s server with the local process runtime on this %s host because required host dependencies are missing or incompatible: %s. Use the Docker runtime instead if you'd like AlphaGSM to provide these dependencies in a container."
        % (action, _current_host_platform_display_name(), "; ".join(failures))
    )


def _running_inside_container():
    """Return whether AlphaGSM is executing inside a container."""

    return os.path.exists("/.dockerenv")


def _current_container_bind_mounts():
    """Return bind-mount source/destination pairs for the current container."""

    if not _running_inside_container():
        return []

    container_name = os.environ.get("HOSTNAME", "").strip()
    if not container_name:
        container_name = socket.gethostname().strip()
    if not container_name:
        return []

    try:
        mounts_json = sp.check_output(
            ["docker", "inspect", "-f", "{{json .Mounts}}", container_name],
            stderr=sp.STDOUT,
            shell=False,
            text=True,
        )
    except (OSError, sp.SubprocessError):
        return []

    try:
        mounts = json.loads(mounts_json or "[]")
    except ValueError:
        return []

    bind_mounts = []
    for mount in mounts:
        if mount.get("Type") != "bind":
            continue
        source = str(mount.get("Source") or "").rstrip(os.sep)
        destination = str(mount.get("Destination") or "").rstrip(os.sep)
        if not source or not destination:
            continue
        bind_mounts.append(
            {
                "source": source or os.sep,
                "destination": destination or os.sep,
            }
        )
    return bind_mounts


def _current_container_identity_mount_roots():
    """Return same-path bind-mount roots when AlphaGSM runs inside Docker."""

    roots = []
    for mount in _current_container_bind_mounts():
        source = mount["source"]
        destination = mount["destination"]
        if source != destination:
            continue
        roots.append(destination or os.sep)
    return roots


class _MountTranslationSnapshot:
    """Cache manager-container bind discovery for one runtime operation."""

    def __init__(self):
        self._discovered = False
        self.inside_container = False
        self.bind_mounts = ()

    def discover(self):
        """Return one immutable view of manager-container mount identity."""

        if not self._discovered:
            self.inside_container = _running_inside_container()
            self.bind_mounts = tuple(copy.deepcopy(_current_container_bind_mounts()))
            self._discovered = True
        return self.inside_container, self.bind_mounts


_ACTIVE_MOUNT_TRANSLATION_SNAPSHOT = contextvars.ContextVar(
    "alphagsm_mount_translation_snapshot",
    default=None,
)


def _mount_translation_snapshot(snapshot=None):
    """Return an explicit, active, or new mount-translation snapshot."""

    return snapshot or _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.get() or _MountTranslationSnapshot()


def _translate_manager_container_path_to_host(path, *, _mount_snapshot=None):
    """Return the host-visible path for *path* when AlphaGSM runs in Docker."""

    if not path:
        return None

    snapshot = _mount_translation_snapshot(_mount_snapshot)
    inside_container, bind_mounts = snapshot.discover()
    absolute_path = os.path.abspath(str(path))
    if not bind_mounts:
        return None if inside_container else absolute_path

    return _translate_path_with_bind_mounts(absolute_path, bind_mounts)


def _translate_path_with_bind_mounts(path, bind_mounts):
    """Translate *path* through one already-discovered bind-mount snapshot."""

    best_match = None
    best_destination = None
    absolute_path = os.path.abspath(str(path))
    for mount in bind_mounts:
        destination = os.path.abspath(str(mount["destination"]))
        source = os.path.abspath(str(mount["source"]))
        try:
            if os.path.commonpath([destination, absolute_path]) != destination:
                continue
        except ValueError:
            continue
        relative_path = os.path.relpath(absolute_path, destination)
        translated = source if relative_path == "." else os.path.join(source, relative_path)
        if best_destination is None or len(destination) > len(best_destination):
            best_match = translated
            best_destination = destination
    return best_match


def _resolve_host_visible_mounts(mounts, *, _mount_snapshot=None):
    """Return mounts translated through one trusted discovery snapshot."""

    snapshot = _mount_translation_snapshot(_mount_snapshot)
    inside_container, bind_mounts = snapshot.discover()
    if not bind_mounts:
        if inside_container:
            sources = [
                str(_mount_source(mount))
                for mount in mounts or ()
                if _mount_source(mount)
            ]
            source_detail = ", ".join(sources) or "<no mount sources>"
            raise RuntimeError(
                "AlphaGSM is running inside a container but cannot establish a "
                "host-visible bind-mount mapping for: {}. Ensure the Docker socket "
                "is available, the current container can be inspected, and "
                "ALPHAGSM_HOME is bind-mounted from the host.".format(source_detail)
            )
        return _normalize_mounts(mounts)

    resolved_mounts = []
    for mount in mounts or ():
        normalized = _normalize_mount(mount)
        source = os.path.abspath(str(normalized["source"]))
        translated = _translate_path_with_bind_mounts(source, bind_mounts)
        if translated is None:
            raise RuntimeError(
                "Docker-backed server paths must live under a host-visible bind mount "
                "when AlphaGSM runs inside Docker. Path not visible to the host "
                "daemon: %s. Use a path under ALPHAGSM_HOME instead." % (source,)
            )
        normalized["source"] = translated
        resolved_mounts.append(normalized)
    return resolved_mounts


def validate_mount_path_identity(mounts, *, _mount_snapshot=None):
    """Reject bind mounts that are not host-visible in manager-container mode."""

    return _resolve_host_visible_mounts(
        mounts,
        _mount_snapshot=_mount_snapshot,
    )


def _host_visible_mount_source(source):
    """Return the Docker-daemon-visible version of *source*."""

    translated = _translate_manager_container_path_to_host(source)
    if translated is None:
        return source
    return translated


def _host_visible_mount_spec(mount):
    """Return *mount* with its source rewritten for the host Docker daemon."""

    if isinstance(mount, dict):
        rewritten = dict(mount)
        if rewritten.get("source"):
            rewritten["source"] = _host_visible_mount_source(rewritten["source"])
        return rewritten

    source, sep, remainder = str(mount).partition(":")
    if not sep or not source:
        return mount
    return _host_visible_mount_source(source) + sep + remainder


def default_install_dir(server):
    """Return the default install directory for *server*.

    Traditional host installs keep using ``~/server-name``. When AlphaGSM runs
    inside the optional manager container, that default is wrong for
    Docker-backed servers because ``/root/<name>`` only exists inside the
    manager. In that mode, prefer the shared same-path mount root and place new
    installs under ``<ALPHAGSM_HOME>/servers/<name>``.
    """

    shared_root = os.environ.get("ALPHAGSM_HOME", "").strip()
    if shared_root or _current_container_identity_mount_roots():
        shared_root = _configured_manager_root()

    if shared_root:
        return os.path.join(shared_root, "servers", server.name)
    return os.path.expanduser(os.path.join("~", server.name))


def suggest_install_dir(server, current_dir=None):
    """Return the best install directory for *server* in the current context."""

    candidate = current_dir or server.data.get("dir")
    if candidate:
        try:
            validate_mount_path_identity(
                [{"source": candidate, "target": DEFAULT_CONTAINER_WORKDIR, "mode": "rw"}]
            )
            return candidate
        except RuntimeError:
            pass
    return default_install_dir(server)


def build_container_spec(
    server,
    *,
    family,
    get_start_command,
    port_definitions=(),
    env=None,
    mounts=None,
    stdin_open=True,
    tty=False,
    working_dir=None,
    extra=None,
    _mount_snapshot=None,
):
    """Build a Docker launch spec from a module start-command hook."""

    mount_snapshot = _mount_translation_snapshot(_mount_snapshot)
    identity_extra = {
        key: extra[key]
        for key in ("run_as_host_user", "container_home")
        if extra and key in extra
    }
    requirements = build_runtime_requirements(
        server,
        family=family,
        port_definitions=port_definitions,
        env=env,
        mounts=mounts,
        extra=identity_extra,
    )
    validate_mount_path_identity(
        list(requirements.get("mounts") or []),
        _mount_snapshot=mount_snapshot,
    )
    command, cwd = get_start_command(server)
    command, mapped_cwd, resolved_mounts = resolve_container_launch_context(
        server,
        mounts=requirements.get("mounts"),
        command=command,
        cwd=cwd,
        _mount_snapshot=mount_snapshot,
    )
    if family == "java" and command:
        command = ["java", *list(command[1:])]
    if working_dir is None:
        if resolved_mounts:
            working_dir = mapped_cwd or DEFAULT_CONTAINER_WORKDIR
        else:
            working_dir = mapped_cwd
    spec = {
        "working_dir": working_dir,
        "stdin_open": stdin_open,
        "tty": tty,
        "env": requirements.get("env", {}),
        "mounts": resolved_mounts,
        "ports": requirements.get("ports", []),
        "command": list(command),
    }
    if extra:
        spec.update(copy.deepcopy(dict(extra)))
    for key in ("run_as_host_user", "container_home"):
        if key in requirements:
            spec[key] = requirements[key]
    return spec


def _mount_covers_path(mount, path):
    """Return whether *mount* already exposes *path* inside the container."""

    if isinstance(mount, dict):
        source = mount.get("source")
    else:
        source = str(mount).split(":", 1)[0]
    if not source:
        return False
    try:
        return os.path.commonpath(
            [os.path.abspath(source), os.path.abspath(path)]
        ) == os.path.abspath(source)
    except ValueError:
        return False


def _map_host_path_into_container(mounts, host_path):
    """Return the container path for *host_path* when it is mounted."""

    if not host_path:
        return None

    host_path_abs = os.path.abspath(host_path)
    host_path_real = os.path.realpath(host_path_abs)
    for mount in mounts or ():
        if isinstance(mount, dict):
            source = mount.get("source")
            target = mount.get("target")
        else:
            source, _sep, remainder = str(mount).partition(":")
            target, _sep, _mode = remainder.partition(":")
        if not source or not target:
            continue
        source_abs = os.path.abspath(source)
        source_real = os.path.realpath(source_abs)
        try:
            if os.path.commonpath([source_real, host_path_real]) != source_real:
                continue
        except ValueError:
            continue
        relative_path = os.path.relpath(host_path_real, source_real)
        if relative_path == ".":
            return str(target)
        return os.path.join(str(target), relative_path).replace("\\", "/")
    return None


def _map_container_path_to_host(mounts, container_path):
    """Return the host path for *container_path* when it is mounted."""

    if not container_path:
        return None

    container_path_abs = os.path.abspath(container_path)
    for mount in mounts or ():
        if isinstance(mount, dict):
            source = mount.get("source")
            target = mount.get("target")
        else:
            source, _sep, remainder = str(mount).partition(":")
            target, _sep, _mode = remainder.partition(":")
        if not source or not target:
            continue
        target_abs = os.path.abspath(str(target))
        try:
            if os.path.commonpath([target_abs, container_path_abs]) != target_abs:
                continue
        except ValueError:
            continue
        relative_path = os.path.relpath(container_path_abs, target_abs)
        source_abs = os.path.abspath(source)
        if relative_path == ".":
            return source_abs
        return os.path.join(source_abs, relative_path)
    return None


def resolve_container_launch_context(
    server,
    *,
    mounts=None,
    command=None,
    cwd=None,
    _mount_snapshot=None,
):
    """Normalize Docker launch context for commands that may escape the server root."""

    resolved_mounts = _add_external_executable_mounts(
        server,
        list(mounts or []),
    )
    validate_mount_path_identity(
        resolved_mounts,
        _mount_snapshot=_mount_translation_snapshot(_mount_snapshot),
    )
    resolved_command, resolved_cwd = _rewrite_external_launcher_context(
        server,
        resolved_mounts,
        command,
        cwd,
    )
    container_cwd = resolved_cwd
    if resolved_mounts:
        container_cwd = _map_host_path_into_container(resolved_mounts, resolved_cwd)
    return list(resolved_command or []), container_cwd, resolved_mounts


def _add_external_executable_mounts(server, mounts):
    """Ensure container mounts include symlink targets used by the executable.

    AlphaGSM often symlinks downloaded payloads from the server directory into the
    shared download cache. Docker runtime mounts only the server directory by
    default, so those symlinks become broken inside the container unless the
    target path is also mounted. Some Steam installs place symlinks on parent
    directories inside the executable path, so walk each path component instead
    of only checking the executable leaf.
    """

    server_dir = server.data.get("dir")
    exe_name = server.data.get("exe_name")
    if not server_dir or not exe_name:
        return mounts

    server_root = os.path.abspath(server_dir)
    real_server_root = os.path.realpath(server_root)
    exe_path = os.path.abspath(os.path.join(server_root, exe_name))
    candidate_paths = []

    try:
        if os.path.commonpath([server_root, exe_path]) == server_root:
            relative_path = os.path.relpath(exe_path, server_root)
            current_path = server_root
            for part in relative_path.split(os.sep):
                if part in ("", "."):
                    continue
                current_path = os.path.join(current_path, part)
                candidate_paths.append(current_path)
        else:
            candidate_paths.append(exe_path)
    except ValueError:
        candidate_paths.append(exe_path)

    for candidate_path in candidate_paths:
        if not os.path.islink(candidate_path):
            continue

        target_path = os.path.realpath(candidate_path)
        try:
            if (
                os.path.commonpath([real_server_root, target_path])
                == real_server_root
            ):
                continue
        except ValueError:
            pass

        if any(_mount_covers_path(mount, target_path) for mount in mounts):
            continue

        mounts.append(
            {
                "source": os.path.dirname(target_path),
                "target": os.path.dirname(target_path),
                "mode": "ro",
            }
        )
    return mounts


def _configured_external_executable_path(server):
    """Return the resolved executable path when it escapes the server root."""

    server_dir = server.data.get("dir")
    exe_name = server.data.get("exe_name")
    if not server_dir or not exe_name:
        return None

    server_root = os.path.realpath(os.path.abspath(server_dir))
    configured_path = os.path.abspath(os.path.join(server_root, exe_name))
    real_path = os.path.realpath(configured_path)
    if not os.path.isfile(real_path):
        return None

    try:
        if os.path.commonpath([server_root, real_path]) == server_root:
            return None
    except ValueError:
        return real_path
    return real_path


def _recover_mounted_install_executable_path(server, mounts, command, cwd):
    """Return a nested install-tree executable path when cwd/command miss it."""

    server_dir = server.data.get("dir")
    exe_name = os.path.basename(str(server.data.get("exe_name", "")))
    if not server_dir or not exe_name or not command:
        return None

    command_index = 0
    while command_index < len(command) and str(command[command_index]) == "env":
        command_index += 1
        while command_index < len(command) and "=" in str(command[command_index]):
            command_index += 1
    if command_index >= len(command):
        return None

    current_executable = str(command[command_index])
    if os.path.basename(current_executable) != exe_name:
        return None
    normalized_executable = current_executable.replace("\\", "/")
    if normalized_executable not in {exe_name, "./" + exe_name}:
        return None

    host_cwd = _map_container_path_to_host(mounts, cwd) or cwd or server_dir
    candidate_path = os.path.abspath(os.path.join(host_cwd, current_executable))
    if os.path.isfile(candidate_path):
        return None

    try:
        return os.path.abspath(
            gamemodule_common.resolve_install_executable(
                server,
                exe_name=exe_name,
                install_dir=server_dir,
            )
        )
    except ServerError:  # pragma: no cover - shared helper normalizes the miss path.
        return None


def _rewrite_external_launcher_context(server, mounts, command, cwd):
    """Rewrite launcher context when the configured executable escapes the mount root."""

    real_path = _configured_external_executable_path(server)
    if real_path is None:
        real_path = _recover_mounted_install_executable_path(server, mounts, command, cwd)
    if real_path is None:
        return command, cwd

    rewritten_command = list(command or [])
    if not rewritten_command:
        return rewritten_command, cwd

    exe_name = os.path.basename(str(server.data.get("exe_name", "")))
    command_index = 0
    if rewritten_command[0] == "env":
        command_index = 1
        while command_index < len(rewritten_command) and "=" in rewritten_command[command_index]:
            command_index += 1
    if command_index >= len(rewritten_command):
        return rewritten_command, cwd

    current_executable = str(rewritten_command[command_index])
    if os.path.basename(current_executable) != exe_name:
        return rewritten_command, cwd

    rewritten_command[command_index] = "./" + os.path.basename(real_path)
    return rewritten_command, os.path.dirname(real_path)


def infer_runtime_requirements(server, module=None):
    """Infer Docker runtime metadata for modules without explicit hooks."""

    module = module or getattr(server, "module", None)
    family = _infer_runtime_family(server, module)

    if family == "wine-proton":
        return proton.get_runtime_requirements(
            server,
            port_definitions=_infer_port_definitions(server, family),
        )

    requirements = build_runtime_requirements(
        server,
        family=family,
        port_definitions=_infer_port_definitions(server, family),
    )
    if family == "java":
        java_major = server.data.get("java_major")
        if java_major is None:
            java_major = infer_minecraft_java_major(server.data.get("version"))
        requirements.update(
            {
                "java": int(java_major),
                "env": {
                    "ALPHAGSM_JAVA_MAJOR": str(java_major),
                    "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
                },
            }
        )
    return requirements


def infer_container_spec(server, *args, module=None, **kwargs):
    """Infer a Docker launch spec for modules without explicit hooks."""

    module = module or getattr(server, "module", None)
    family = _infer_runtime_family(server, module)
    get_start_command = getattr(module, "get_start_command", None)

    if family == "wine-proton" and callable(get_start_command):
        return proton.get_container_spec(
            server,
            lambda current_server: get_start_command(current_server, *args, **kwargs),
            port_definitions=_infer_port_definitions(server, family),
        )

    requirements = infer_runtime_requirements(server, module=module)
    if callable(get_start_command):
        command, cwd = get_start_command(server, *args, **kwargs)
    else:
        command, cwd = [], None
    working_dir = cwd
    if requirements.get("mounts"):
        working_dir = DEFAULT_CONTAINER_WORKDIR
    return {
        "working_dir": working_dir,
        "stdin_open": family != "simple-tcp",
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": command,
    }


def ensure_runtime_hooks(module):
    """Attach inferred runtime hooks to modules that do not define them."""

    if module is None:
        return module
    if not _has_explicit_module_hook(module, "get_runtime_requirements"):
        setattr(
            module,
            "get_runtime_requirements",
            lambda server, _module=module: infer_runtime_requirements(server, module=_module),
        )
    if not _has_explicit_module_hook(module, "get_container_spec"):
        setattr(
            module,
            "get_container_spec",
            lambda server, *args, _module=module, **kwargs: infer_container_spec(
                server,
                module=_module,
                *args,
                **kwargs,
            ),
        )
    return module


def normalize_runtime_requirements(requirements, server_name):
    """Normalise a runtime-requirements mapping."""

    req = dict(requirements or {})
    if "install_requirements" in req and "host_dependencies" not in req:
        req["host_dependencies"] = req.pop("install_requirements")
    if "engine" in req and "runtime" not in req:
        req["runtime"] = req.pop("engine")
    if "family" in req and "runtime_family" not in req:
        req["runtime_family"] = req.pop("family")
    if "runtime_family" in req:
        req["runtime_family"] = canonicalize_runtime_family(req["runtime_family"])
    if "java" in req and "java_major" not in req:
        req["java_major"] = req.pop("java")
    if "host_dependencies" in req:
        req["host_dependencies"] = _normalize_host_dependency_specs(
            req["host_dependencies"],
            server_name,
        )
    return req


def _copy_metadata_value(value):
    """Return an isolated copy of a metadata value."""

    return copy.deepcopy(value)


def _existing_runtime_metadata(server):
    """Return stored runtime metadata from the server datastore."""

    return {
        key: _copy_metadata_value(server.data[key])
        for key in RUNTIME_DATA_KEYS
        if key in server.data
    }


def _get_configured_runtime_name():
    """Return the configured runtime backend name."""

    configured = settings.user.getsection("runtime").get("backend", "process")
    configured = str(configured).strip().lower()
    if configured == "":
        return "process"
    if configured not in VALID_RUNTIME_BACKENDS:
        raise RuntimeError("Unknown runtime backend: '" + configured + "'")
    return configured


def _ci_runtime_image_override(family):
    """Return the GitHub CI runtime-image override for *family*, if any."""

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return ""

    family_key = "ALPHAGSM_BACKEND_DOCKER_IMAGE_" + str(family or "").upper().replace("-", "_")
    return (
        os.environ.get(family_key, "").strip()
        or os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE", "").strip()
    )


def resolve_runtime_metadata(server, *, requirements=None):
    """Resolve the effective runtime metadata for *server*."""

    existing = _existing_runtime_metadata(server)
    module = getattr(server, "module", None)
    if module is not None:
        ensure_runtime_hooks(module)
    if requirements is None:
        hook = (
            _get_module_hook(module, "get_runtime_requirements")
            if module is not None
            else None
        )
        requirements = normalize_runtime_requirements(
            hook(server)
            if hook is not None
            else infer_runtime_requirements(server, module=module),
            server.name,
        )
    else:
        requirements = normalize_runtime_requirements(requirements, server.name)
    configured_runtime = _get_configured_runtime_name()

    if not requirements and not existing:
        return {}

    if configured_runtime != "docker":
        return {"runtime": "process"}

    runtime_name = requirements.get("runtime", existing.get("runtime", "process"))
    if runtime_name != "docker":
        if "runtime" in requirements or "runtime" in existing:
            return {"runtime": runtime_name}
        return {}

    family = canonicalize_runtime_family(
        requirements.get("runtime_family", existing.get("runtime_family"))
    )
    defaults = copy.deepcopy(RUNTIME_FAMILY_DEFAULTS.get(family, {}))
    metadata = {}
    metadata.update(defaults)
    metadata.update(existing)
    metadata.update(requirements)
    metadata["runtime"] = "docker"
    if family is not None:
        metadata["runtime_family"] = family
    metadata.setdefault("container_name", "alphagsm-" + server.name)
    metadata.setdefault("network_mode", "bridge")
    metadata.setdefault("stop_mode", "docker-stop")
    metadata.setdefault("env", {})
    metadata.setdefault("mounts", [])
    metadata.setdefault("ports", [])

    default_image = defaults.get("image", "")
    override_image = _ci_runtime_image_override(metadata.get("runtime_family"))
    if override_image and metadata.get("image", "") in ("", default_image):
        metadata["image"] = override_image

    if (
        metadata.get("runtime_family") == "java"
        and metadata.get("stop_mode") == "exec-console"
        and not metadata.get("stdin_open")
        and not metadata.get("tty")
    ):
        metadata["stop_mode"] = "docker-stop"

    version = server.data.get("version")
    if metadata.get("runtime_family") == "java" and version not in (None, "", "latest"):
        inferred_java_major = infer_minecraft_java_major(version)
        current_java_major = metadata.get("java_major")
        try:
            current_java_major = int(current_java_major)
        except (TypeError, ValueError):
            current_java_major = None
        if current_java_major is None or current_java_major < inferred_java_major:
            metadata["java_major"] = inferred_java_major
            metadata["env"] = dict(metadata.get("env") or {})
            metadata["env"]["ALPHAGSM_JAVA_MAJOR"] = str(inferred_java_major)

    return metadata


def sync_runtime_metadata(server, save=False):
    """Persist resolved runtime metadata into the server datastore."""

    metadata = resolve_runtime_metadata(server)
    existing = _existing_runtime_metadata(server)
    if metadata == {"runtime": "process"} and not existing:
        return False
    changed = False
    for key in RUNTIME_DATA_KEYS:
        if key in server.data and key not in metadata:
            del server.data[key]
            changed = True
    for key, value in metadata.items():
        if server.data.get(key) != value:
            server.data[key] = _copy_metadata_value(value)
            changed = True
    if save and changed and hasattr(server.data, "save"):
        server.data.save()
    return changed


def infer_minecraft_java_major(version):
    """Return the preferred Java major for a Minecraft server version string."""

    if not version:
        return 21
    version = str(version).strip().lower()
    if version == "latest":
        return 21
    parts = version.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        if major >= 26:
            return 25
        if (major, minor) < (1, 17):
            return 8
        if (major, minor) < (1, 20):
            return 17
        if (major, minor) == (1, 20) and patch < 5:
            return 17
        return 21
    return 21


def _running_inside_container():
    """Return whether AlphaGSM appears to be running inside a container."""

    return os.path.exists("/.dockerenv")


def _inspect_container_network_value(container_name, field):
    """Return the first valid network IP from a Docker inspect *field*."""

    try:
        raw = sp.check_output(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{println ." + field + "}}{{end}}",
                container_name,
            ],
            stderr=sp.STDOUT,
            shell=False,
            text=True,
        )
    except (OSError, sp.SubprocessError):
        return ""

    for line in raw.splitlines():
        line = line.strip()
        if not line or line == "<no value>":
            continue
        try:
            ipaddress.ip_address(line)
        except ValueError:
            continue
        return line
    return ""


def resolve_query_host(server, default="127.0.0.1"):
    """Return the best reachable host for query/info checks.

    Docker-backed servers are queried from two different contexts in tests:
    directly from the host runner, and from a manager container that launches a
    sibling game container through the Docker socket. In the latter case,
    ``127.0.0.1`` points at the manager container rather than the game server.

    When the runtime backend is Docker, prefer an explicit external IP if the
    user configured one. Inside a containerized manager, prefer the target
    container's bridge gateway so published host ports remain reachable from the
    manager. Otherwise fall back to *default* so host-side AlphaGSM continues to
    use loopback-host published ports by default.
    """

    explicit_host = str(
        server.data.get("publicip")
        or server.data.get("externalip")
        or server.data.get("hostip")
        or server.data.get("bindaddress")
        or ""
    ).strip()
    if explicit_host and explicit_host not in {"0.0.0.0", "::", "<no value>"}:
        return explicit_host

    if not hasattr(server, "name"):
        return default

    metadata = resolve_runtime_metadata(server)
    if metadata.get("runtime") != "docker":
        return default

    container_name = metadata.get("container_name")
    if not container_name:
        return default

    if _running_inside_container():
        gateway = _inspect_container_network_value(container_name, "Gateway")
        if gateway:
            return gateway
        container_ip = _inspect_container_network_value(container_name, "IPAddress")
        if container_ip:
            return container_ip

    return default


def handles_set_key(key):
    """Return whether *key* should be validated by the runtime layer."""

    if not key:
        return False
    top_level = key[0]
    return top_level in {
        "runtime",
        "runtime_family",
        "image",
        "java_major",
        "container_name",
        "network_mode",
        "stop_mode",
    } or (top_level == "env" and len(key) > 1)


def validate_set_value(server, key, *value):
    """Validate a datastore mutation for runtime-managed keys."""

    if not handles_set_key(key):
        raise RuntimeError("Runtime layer does not manage key: " + ".".join(key))

    top_level = key[0]
    if top_level == "runtime":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'runtime'")
        runtime_name = str(value[0]).strip().lower()
        if runtime_name not in VALID_RUNTIME_BACKENDS:
            raise RuntimeError("Unsupported runtime backend: " + runtime_name)
        return runtime_name

    if top_level == "runtime_family":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'runtime_family'")
        family = canonicalize_runtime_family(value[0])
        if not family:
            raise RuntimeError("runtime_family cannot be empty")
        return family

    if top_level == "image":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'image'")
        image = str(value[0]).strip()
        if not image:
            raise RuntimeError("image cannot be empty")
        return image

    if top_level == "java_major":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'java_major'")
        java_major = int(value[0])
        if java_major <= 0:
            raise RuntimeError("java_major must be greater than zero")
        return java_major

    if top_level == "container_name":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'container_name'")
        container_name = str(value[0]).strip()
        if not container_name:
            raise RuntimeError("container_name cannot be empty")
        return container_name

    if top_level == "network_mode":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'network_mode'")
        network_mode = str(value[0]).strip()
        if not network_mode:
            raise RuntimeError("network_mode cannot be empty")
        return network_mode

    if top_level == "stop_mode":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for 'stop_mode'")
        stop_mode = str(value[0]).strip().lower()
        if stop_mode not in VALID_STOP_MODES:
            raise RuntimeError("Unsupported stop_mode: " + stop_mode)
        return stop_mode

    if top_level == "env":
        if len(value) != 1:
            raise RuntimeError("Only one value supported for runtime env entries")
        return str(value[0])

    raise RuntimeError("Unsupported runtime key: " + ".".join(key))


def get_container_spec(
    server,
    *args,
    _runtime_requirements=None,
    _mount_snapshot=None,
    **kwargs,
):
    """Return the effective container spec for *server*."""

    mount_snapshot = _mount_translation_snapshot(_mount_snapshot)
    module = getattr(server, "module", None)
    if module is not None:
        ensure_runtime_hooks(module)
    hook = _get_module_hook(module, "get_container_spec") if module is not None else None
    snapshot_token = _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.set(mount_snapshot)
    try:
        if hook is not None:
            spec = hook(server, *args, **kwargs) or {}
        else:
            spec = infer_container_spec(server, module=module, *args, **kwargs)
    finally:
        _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.reset(snapshot_token)
    merged = resolve_runtime_metadata(
        server,
        requirements=_runtime_requirements,
    )
    merged.update(spec)
    merged.setdefault("container_name", "alphagsm-" + server.name)
    merged.setdefault("env", {})
    merged.setdefault("mounts", [])
    merged.setdefault("ports", [])
    if merged.get("runtime_family") == "java":
        if merged.get("stop_mode") == "exec-console":
            if not merged.get("stdin_open") and not merged.get("tty"):
                merged["stop_mode"] = "docker-stop"
        elif merged.get("stdin_open") or merged.get("tty"):
            merged["stop_mode"] = "exec-console"
    merged["mounts"] = _add_external_executable_mounts(
        server, list(merged.get("mounts") or [])
    )
    merged["mounts"] = _normalize_mounts(merged["mounts"])
    validate_mount_path_identity(
        merged["mounts"],
        _mount_snapshot=mount_snapshot,
    )
    merged["command"], merged["working_dir"] = _rewrite_external_launcher_context(
        server,
        merged["mounts"],
        merged.get("command"),
        merged.get("working_dir"),
    )
    mapped_working_dir = _map_host_path_into_container(
        merged["mounts"], merged.get("working_dir")
    )
    if mapped_working_dir is not None:
        merged["working_dir"] = mapped_working_dir
    return merged


def _get_module_runtime_requirements(server):
    """Return normalized module-declared runtime requirements for *server*."""

    module = getattr(server, "module", None)
    if module is not None:
        ensure_runtime_hooks(module)
    hook = _get_module_hook(module, "get_runtime_requirements") if module is not None else None
    if hook is None:
        return {}
    return normalize_runtime_requirements(hook(server) or {}, server.name)


def get_runtime_doctor_report(server):
    """Return a runtime diagnostics snapshot for *server*."""

    report = {
        "server": server.name,
    }
    try:
        report["configured_backend"] = _get_configured_runtime_name()
    except RuntimeError as ex:
        report["configured_backend_error"] = str(ex)
        return report

    try:
        module_requirements = _get_module_runtime_requirements(server)
    except Exception as ex:  # pragma: no cover - defensive diagnostics path
        report["module_runtime_error"] = str(ex)
        return report

    if module_requirements:
        report["module_runtime"] = module_requirements.get("runtime", "process")
        if module_requirements.get("runtime_family"):
            report["module_runtime_family"] = module_requirements["runtime_family"]

    try:
        metadata = resolve_runtime_metadata(
            server,
            requirements=module_requirements,
        )
    except Exception as ex:  # pragma: no cover - defensive diagnostics path
        report["runtime_resolution_error"] = str(ex)
        return report

    runtime_name = metadata.get("runtime", "process")
    report["resolved_runtime"] = runtime_name
    runtime = ContainerRuntime() if runtime_name == "docker" else ProcessRuntime()
    if runtime_name == "docker":
        report["running"] = False
    else:
        report["running"] = runtime.is_running(server)

    if runtime_name == "docker":
        host_report = {
            "applicable": False,
            "skipped_reason": "docker runtime supplies its own dependencies",
        }
    else:
        try:
            host_report = get_process_host_dependency_report(server)
        except Exception as ex:  # pragma: no cover - defensive diagnostics path
            report["host_requirements_error"] = str(ex)
            return report

    if host_report.get("applicable"):
        report["host_requirements_ok"] = host_report.get("ok", True)
        report["host_requirements"] = host_report.get("requirements", [])
    elif host_report.get("skipped_reason"):
        report["host_requirements_skipped"] = host_report["skipped_reason"]

    if runtime_name != "docker":
        return report

    report["runtime_family"] = metadata.get("runtime_family", "unknown")
    report["image"] = metadata.get("image", "")
    report["container_name"] = metadata.get("container_name", "")
    report["network_mode"] = metadata.get("network_mode", "")
    report["stop_mode"] = metadata.get("stop_mode", "")

    identity = None
    if module_requirements.get("run_as_host_user", False):
        report["run_as_host_user"] = True
        try:
            identity = _resolve_effective_host_user(reject_root=False)
            report["effective_user"] = _format_effective_host_user(identity)
            _validate_requirement_identity_before_spec(
                module_requirements, identity
            )
        except RuntimeError as ex:
            report["host_user_identity_error"] = str(ex)
            report["container_identity_error"] = str(ex)
            report["container_home_error"] = str(ex)
            return report

    mount_snapshot = _MountTranslationSnapshot()
    try:
        spec = get_container_spec(
            server,
            _runtime_requirements=module_requirements,
            _mount_snapshot=mount_snapshot,
        )
    except Exception as ex:  # pragma: no cover - defensive diagnostics path
        report["container_spec_error"] = str(ex)
        return report

    report["working_dir"] = spec.get("working_dir", "")
    report["command"] = list(spec.get("command", ()))
    report["mounts"] = copy.deepcopy(spec.get("mounts", []))
    report["ports"] = copy.deepcopy(spec.get("ports", []))
    report["mount_count"] = len(spec.get("mounts") or ())
    report["port_count"] = len(spec.get("ports") or ())
    try:
        _validate_container_identity_contract(module_requirements, spec)
    except RuntimeError as ex:
        report["container_identity_error"] = str(ex)
        report["container_home_error"] = str(ex)
        return report
    if module_requirements.get("run_as_host_user", False):
        try:
            container_home = _container_home_from_spec(spec)
        except RuntimeError as ex:
            report["host_user_identity_error"] = str(ex)
            report["container_identity_error"] = str(ex)
            report["container_home_error"] = str(ex)
        else:
            report["home"] = container_home
            home_mount = _find_container_home_mount(spec, container_home)
            if home_mount is not None:
                report["container_home_mount"] = copy.deepcopy(home_mount)
                report["container_home_mount_writable"] = not _mount_is_read_only(
                    home_mount
                )
                home_source = _mount_source(home_mount)
                if home_source:
                    report["container_home_source"] = home_source
            try:
                home_plan = _validate_host_user_container_home(
                    server, spec, identity
                )
            except RuntimeError as ex:
                report["container_home_error"] = str(ex)
                return report
            else:
                report["container_home_source_exists"] = home_plan[
                    "home_source_exists"
                ]
                report["container_home_source_writable"] = home_plan[
                    "home_source_writable"
                ]
                report["container_home_source_creatable"] = home_plan[
                    "home_source_creatable"
                ]

    try:
        snapshot_token = _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.set(mount_snapshot)
        try:
            runtime.validate_mount_path_identity(spec)
        finally:
            _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.reset(snapshot_token)
        if module_requirements.get("run_as_host_user", False):
            _validate_host_visible_host_user_home_overlap(spec)
        report["mount_path_identity"] = "ok"
    except RuntimeError as ex:
        report["mount_path_identity_error"] = str(ex)
        if module_requirements.get("run_as_host_user", False):
            report["container_home_error"] = str(ex)
        return report

    try:
        docker_cli = runtime.docker_cli_version()
        report["docker_cli"] = docker_cli or "ok"
    except RuntimeError as ex:
        report["docker_cli_error"] = str(ex)
        return report

    image = spec.get("image")
    if image:
        report["image_present"] = runtime.image_exists(image)

    container_name = spec.get("container_name")
    if container_name:
        container_state = runtime.container_running_state(container_name)
        if container_state is True:
            report["container_state"] = "running"
            report["running"] = True
        elif container_state is False:
            report["container_state"] = "stopped"
            report["running"] = False
        else:
            report["container_state"] = "missing"
            report["running"] = False

    return report


def print_runtime_doctor_report(server):
    """Print a human-readable runtime diagnostics snapshot for *server*."""

    report = get_runtime_doctor_report(server)
    print("Runtime doctor for " + server.name)

    configured_backend = report.get("configured_backend")
    if configured_backend is not None:
        print("Configured backend: " + configured_backend)
    if "configured_backend_error" in report:
        print("Backend error: " + report["configured_backend_error"])
        return report

    module_runtime = report.get("module_runtime")
    if module_runtime is not None:
        line = "Module runtime preference: " + module_runtime
        module_family = report.get("module_runtime_family")
        if module_family:
            line += " (family " + module_family + ")"
        print(line)

    resolved_runtime = report.get("resolved_runtime", "unknown")
    print("Resolved runtime: " + resolved_runtime)
    print("Currently running: " + ("yes" if report.get("running") else "no"))

    host_requirements = report.get("host_requirements") or []
    if host_requirements:
        print("Host requirements:")
        for requirement in host_requirements:
            line = "  - {display_name}: ".format(**requirement)
            if requirement.get("ok"):
                if "installed_major" in requirement and "minimum_major" in requirement:
                    line += "ok (found {installed_major}, need {minimum_major}+)".format(
                        **requirement
                    )
                else:
                    line += "ok"
            else:
                line += requirement.get("error", "failed")
            print(line)
    elif "host_requirements_skipped" in report:
        print("Host requirements: " + report["host_requirements_skipped"])
    if "host_requirements_error" in report:
        print("Host requirements error: " + report["host_requirements_error"])
        return report

    if "module_runtime_error" in report:
        print("Module runtime error: " + report["module_runtime_error"])
        return report
    if "runtime_resolution_error" in report:
        print("Runtime resolution error: " + report["runtime_resolution_error"])
        return report
    if resolved_runtime != "docker":
        return report

    print("Runtime family: " + report.get("runtime_family", "unknown"))
    print("Image: " + report.get("image", ""))
    print("Container name: " + report.get("container_name", ""))
    print("Network mode: " + report.get("network_mode", ""))
    print("Stop mode: " + report.get("stop_mode", ""))
    if "container_identity_error" in report:
        print("Container identity error: " + report["container_identity_error"])
    if report.get("run_as_host_user", False):
        if "effective_user" in report:
            print("Effective container user: " + report["effective_user"])
        if "host_user_identity_error" in report:
            print("Container user error: " + report["host_user_identity_error"])
        if report.get("home"):
            print("Container HOME: " + report["home"])
        if "container_home_mount_writable" in report:
            print(
                "Container HOME mount writable: "
                + ("yes" if report["container_home_mount_writable"] else "no")
            )
        if "container_home_source_writable" in report:
            print(
                "Container HOME host source writable: "
                + ("yes" if report["container_home_source_writable"] else "no")
            )
        if "container_home_source_exists" in report:
            print(
                "Container HOME host source exists: "
                + ("yes" if report["container_home_source_exists"] else "no")
            )
        if "container_home_source_creatable" in report:
            print(
                "Container HOME host source safely creatable: "
                + ("yes" if report["container_home_source_creatable"] else "no")
            )
        if (
            "container_home_error" in report
            and report["container_home_error"]
            != report.get("container_identity_error")
        ):
            print("Container HOME error: " + report["container_home_error"])
    working_dir = report.get("working_dir")
    if working_dir:
        print("Working dir: " + working_dir)
    command = report.get("command") or []
    if command:
        print("Command: " + shlex.join(command))
    mounts = report.get("mounts") or []
    if mounts:
        print("Mounts:")
        for mount in mounts:
            if isinstance(mount, dict):
                mount_line = "{source} -> {target} [{mode}]".format(
                    source=mount.get("source", ""),
                    target=mount.get("target", ""),
                    mode=mount.get("mode", "rw"),
                )
            else:
                mount_line = str(mount)
            print("  - " + mount_line)
    ports = report.get("ports") or []
    if ports:
        print("Ports:")
        for port in ports:
            if isinstance(port, dict):
                port_line = "{host}:{container}/{protocol}".format(
                    host=port.get("host", ""),
                    container=port.get("container", ""),
                    protocol=port.get("protocol", "tcp"),
                )
            else:
                port_line = str(port)
            print("  - " + port_line)
    print("Mount entries: " + str(report.get("mount_count", 0)))
    print("Published ports: " + str(report.get("port_count", 0)))

    if "container_spec_error" in report:
        print("Container spec error: " + report["container_spec_error"])
        return report

    if "docker_cli" in report:
        print("Docker CLI: ok (client " + report["docker_cli"] + ")")
    else:
        print("Docker CLI: error")
    if "docker_cli_error" in report:
        print("Docker CLI error: " + report["docker_cli_error"])
        return report

    if "image_present" in report:
        print("Image present locally: " + ("yes" if report["image_present"] else "no"))
    if "container_state" in report:
        print("Container state: " + report["container_state"])
    if "mount_path_identity_error" in report:
        print("Mount path identity: error")
        print(report["mount_path_identity_error"])
    elif "mount_path_identity" in report:
        print("Mount path identity: " + report["mount_path_identity"])
    return report


class BaseRuntime:
    """Base runtime surface."""

    runtime_name = "runtime"
    running_description = "runtime is running"
    missing_description = "runtime is not running"

    def start(self, server, *args, **kwargs):
        """Start *server*."""
        raise NotImplementedError

    def is_running(self, server):
        """Return whether *server* is running."""
        raise NotImplementedError

    def kill(self, server):
        """Force-kill *server*."""
        raise NotImplementedError

    def send_input(self, server, text):
        """Send console input to *server*."""
        raise NotImplementedError

    def connect(self, server):
        """Connect to the live server session."""
        raise NotImplementedError

    def show_logs(self, server, lines=50):
        """Display recent runtime logs for *server*."""
        raise NotImplementedError


class ProcessRuntime(BaseRuntime):
    """Adapter over the existing screen/tmux/subprocess facade."""

    runtime_name = "process"
    running_description = "screen session exists"
    missing_description = "no screen session"

    def start(self, server, *args, **kwargs):
        assert_host_install_requirements(server, phase="start")
        command, cwd = server.module.get_start_command(server, *args, **kwargs)
        screen.start_screen(server.name, command, cwd=cwd)

    def is_running(self, server):
        return screen.check_screen_exists(server.name)

    def kill(self, server):
        screen.send_to_screen(server.name, ["quit"])

    def send_input(self, server, text):
        screen.send_to_server(server.name, text)

    def connect(self, server):
        screen.connect_to_screen(server.name)

    def show_logs(self, server, lines=50):
        log_file = screen.logpath(server.name)
        if not os.path.isfile(log_file):
            raise RuntimeError("No log file found at: " + log_file)
        result = sp.run(["tail", "-n", str(lines), log_file], check=False)
        if result.returncode != 0:
            raise RuntimeError("Failed to read log file: " + log_file)


def _resolve_effective_host_user(*, reject_root):
    """Return the current effective UID/GID without storing it on the server."""

    if not hasattr(os, "geteuid") or not hasattr(os, "getegid"):
        raise RuntimeError(
            "run_as_host_user requires a host with effective UID/GID support"
        )
    effective_uid = os.geteuid()
    effective_gid = os.getegid()
    if reject_root and effective_uid == 0:
        raise RuntimeError(
            "Cannot launch a run_as_host_user container because AlphaGSM's "
            "effective UID is 0; run AlphaGSM as a non-root user"
        )
    return effective_uid, effective_gid


def _format_effective_host_user(identity):
    """Return an effective UID/GID tuple in Docker's user format."""

    return "{}:{}".format(*identity)


def _requirements_container_home(requirements):
    """Return the authoritative HOME declared by runtime requirements."""

    return _normalize_container_home(
        (requirements.get("env") or {}).get("HOME")
        or requirements.get("container_home")
        or DEFAULT_HOST_USER_CONTAINER_HOME
    )


def _validate_requirement_identity_before_spec(requirements, identity):
    """Reject an unusable declared host identity before spec side effects."""

    if not requirements.get("run_as_host_user", False):
        return
    effective_uid, _effective_gid = identity
    if effective_uid == 0:
        raise RuntimeError(
            "Cannot launch a run_as_host_user container because AlphaGSM's "
            "effective UID is 0; run AlphaGSM as a non-root user"
        )


def _validate_container_identity_contract(requirements, spec):
    """Require final spec identity metadata to match module requirements."""

    required_opt_in = bool(requirements.get("run_as_host_user", False))
    spec_opt_in = bool(spec.get("run_as_host_user", False))
    if spec_opt_in != required_opt_in:
        raise RuntimeError(
            "Final container spec run_as_host_user={} does not match authoritative "
            "runtime requirements run_as_host_user={}".format(
                str(spec_opt_in).lower(), str(required_opt_in).lower()
            )
        )
    if not required_opt_in:
        return None

    required_home = _requirements_container_home(requirements)
    spec_home = _normalize_container_home(
        spec.get("container_home") or required_home
    )
    spec_env_home = _normalize_container_home(
        (spec.get("env") or {}).get("HOME") or required_home
    )
    if spec_home != required_home or spec_env_home != required_home:
        raise RuntimeError(
            "Final container spec container_home does not match authoritative "
            "runtime requirements: required {}, spec container_home {}, spec HOME {}".format(
                required_home, spec_home, spec_env_home
            )
        )
    return required_home


def _container_home_from_spec(spec):
    """Resolve the effective HOME for a host-user container spec."""

    explicit_home = (spec.get("env") or {}).get("HOME")
    return _normalize_container_home(
        explicit_home
        or spec.get("container_home")
        or DEFAULT_HOST_USER_CONTAINER_HOME
    )


def _find_container_home_mount(spec, container_home):
    """Return the mount that owns the opted-in container HOME."""

    for mount in spec.get("mounts", ()):
        if _mount_target(mount) == container_home:
            return mount
    return None


def _validate_secure_runtime_directory(path, path_stat, effective_uid):
    """Reject unsafe manager runtime-state directory metadata."""

    if stat.S_ISLNK(path_stat.st_mode):
        raise RuntimeError(
            "Container HOME runtime state must not contain a symbolic link: "
            + path
        )
    if not stat.S_ISDIR(path_stat.st_mode):
        raise RuntimeError(
            "Container HOME runtime state component is not a directory: " + path
        )
    if path_stat.st_uid != effective_uid:
        raise RuntimeError(
            "Container HOME runtime state must be owned by effective UID {}: {}".format(
                effective_uid, path
            )
        )
    mode = stat.S_IMODE(path_stat.st_mode)
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError(
            "Container HOME runtime state must not be group- or world-writable: "
            + path
        )
    owner_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    if mode & owner_permissions != owner_permissions:
        raise RuntimeError(
            "Container HOME runtime state requires owner read, write, and execute "
            "permissions for effective UID {}: {}".format(effective_uid, path)
        )


def _inspect_secure_runtime_path(manager_root, relative_path, effective_uid):
    """Validate one state path without creating it; return whether it exists."""

    try:
        root_stat = os.lstat(manager_root)
    except FileNotFoundError as ex:
        raise RuntimeError(
            "Manager state root does not exist for container HOME: " + manager_root
        ) from ex
    except OSError as ex:
        raise RuntimeError(
            "Unable to inspect manager state root {}: {}".format(manager_root, ex)
        ) from ex
    _validate_secure_runtime_directory(manager_root, root_stat, effective_uid)

    current_path = manager_root
    path_exists = True
    for component in relative_path.split(os.sep):
        if not component or component in (".", ".."):
            raise RuntimeError("Invalid container HOME runtime-state path")
        current_path = os.path.join(current_path, component)
        if not path_exists:
            continue
        try:
            current_stat = os.lstat(current_path)
        except FileNotFoundError:
            path_exists = False
            continue
        except OSError as ex:
            raise RuntimeError(
                "Unable to inspect container HOME runtime state {}: {}".format(
                    current_path, ex
                )
            ) from ex
        _validate_secure_runtime_directory(
            current_path, current_stat, effective_uid
        )
    return path_exists


def _nested_container_home_paths(spec, container_home, home_relative_path):
    """Return state-tree paths required by mounts nested below HOME."""

    nested_paths = []
    for mount in spec.get("mounts", ()):
        mount_target = posixpath.normpath(str(_mount_target(mount)))
        try:
            nested = (
                mount_target != container_home
                and posixpath.commonpath([container_home, mount_target])
                == container_home
            )
        except ValueError:
            nested = False
        if not nested:
            continue
        relative_target = posixpath.relpath(mount_target, container_home)
        nested_paths.append(
            os.path.join(home_relative_path, *relative_target.split("/"))
        )
    return nested_paths


def _reject_symlinked_writable_mount_sources(spec):
    """Reject writable bind sources whose normalized path traverses a symlink."""

    for mount in spec.get("mounts", ()):
        if _mount_is_read_only(mount):
            continue
        source = str(_mount_source(mount) or "")
        if not source:
            continue
        normalized_source = os.path.abspath(os.path.expanduser(source))
        try:
            resolved_source = os.path.realpath(normalized_source)
        except OSError as ex:
            raise RuntimeError(
                "Unable to resolve run_as_host_user writable bind mount source: "
                + normalized_source
            ) from ex
        if resolved_source != normalized_source:
            raise RuntimeError(
                "run_as_host_user writable bind mount source must not contain "
                "symbolic links: " + normalized_source
            )


def _validate_host_user_container_home(server, spec, identity):
    """Return a non-mutating secure creation plan for opted-in HOME state."""

    effective_uid, _effective_gid = identity
    if effective_uid == 0:
        raise RuntimeError(
            "Cannot launch a run_as_host_user container because AlphaGSM's "
            "effective UID is 0; run AlphaGSM as a non-root user"
        )
    _secure_directory_open_flags()

    container_home = _container_home_from_spec(spec)
    spec["container_home"] = container_home
    spec["env"] = dict(spec.get("env") or {})
    spec["env"].setdefault("HOME", container_home)
    spec["mounts"] = list(spec.get("mounts") or ())
    for index, mount in enumerate(spec["mounts"]):
        if _mount_is_read_only(mount):
            continue
        source = _mount_source(mount)
        if not source or not os.path.isabs(str(source)):
            raise RuntimeError(
                "run_as_host_user writable bind mount source must be absolute: "
                + str(source or "<missing>")
            )
        canonical_source = os.path.abspath(os.path.expanduser(str(source)))
        if isinstance(mount, dict):
            mount["source"] = canonical_source
        else:
            normalized_mount = _normalize_mount(mount)
            normalized_mount["source"] = canonical_source
            spec["mounts"][index] = normalized_mount

    _reject_symlinked_writable_mount_sources(spec)

    home_mount = _find_container_home_mount(spec, container_home)
    if home_mount is None:
        raise RuntimeError(
            "run_as_host_user requires a writable bind mount at container HOME "
            + container_home
        )
    if _mount_is_read_only(home_mount):
        raise RuntimeError(
            "run_as_host_user requires a writable container HOME mount: "
            + container_home
        )

    home_source = _mount_source(home_mount)
    if not home_source or not os.path.isabs(home_source):
        raise RuntimeError(
            "run_as_host_user requires an absolute host directory for container HOME "
            + container_home
        )
    manager_root = _configured_manager_root()
    expected_source = _server_runtime_home_source(server)
    normalized_source = str(home_source)
    if normalized_source != expected_source:
        raise RuntimeError(
            "run_as_host_user container HOME must use the manager-owned per-server "
            "runtime state path {} (got {})".format(
                expected_source, normalized_source
            )
        )
    for mount in spec.get("mounts", ()):
        if _mount_target(mount) == container_home or _mount_is_read_only(mount):
            continue
        other_source = _mount_source(mount)
        if not other_source or not os.path.isabs(other_source):
            continue
        other_source = str(other_source)
        try:
            home_is_nested = (
                os.path.commonpath([other_source, expected_source])
                == other_source
            )
        except ValueError:
            home_is_nested = False
        if home_is_nested:
            raise RuntimeError(
                "Container HOME runtime state must not be inside another writable "
                "bind mount: " + other_source
            )
    try:
        if os.path.commonpath([manager_root, expected_source]) != manager_root:
            raise ValueError
    except ValueError as ex:
        raise RuntimeError(
            "Container HOME runtime state escapes the manager-owned root"
        ) from ex

    home_relative_path = os.path.relpath(expected_source, manager_root)
    home_exists = _inspect_secure_runtime_path(
        manager_root, home_relative_path, effective_uid
    )
    relative_paths = [home_relative_path]
    relative_paths.extend(
        _nested_container_home_paths(spec, container_home, home_relative_path)
    )
    for relative_path in relative_paths[1:]:
        _inspect_secure_runtime_path(manager_root, relative_path, effective_uid)
    generated_files = []
    steam_library_state = _steam_runtime_library_state(
        server, spec, home_relative_path
    )
    if steam_library_state is not None:
        steam_library_directory = os.path.dirname(
            steam_library_state["relative_file"]
        )
        relative_paths.append(steam_library_directory)
        _inspect_secure_runtime_path(
            manager_root, steam_library_directory, effective_uid
        )
        generated_files.append(steam_library_state)
    return {
        "manager_root": manager_root,
        "relative_paths": tuple(dict.fromkeys(relative_paths)),
        "generated_files": tuple(generated_files),
        "container_home": container_home,
        "home_mount": home_mount,
        "home_source": expected_source,
        "home_source_exists": home_exists,
        "home_source_writable": home_exists,
        "home_source_creatable": not home_exists,
    }


def _validate_host_visible_host_user_home_overlap(spec):
    """Reject translated writable mounts that contain the HOME source."""

    _reject_symlinked_writable_mount_sources(spec)
    container_home = _container_home_from_spec(spec)
    home_mount = _find_container_home_mount(spec, container_home)
    if home_mount is None or _mount_is_read_only(home_mount):
        return
    home_source = str(_mount_source(home_mount) or "")
    if not home_source:
        return

    for mount in spec.get("mounts", ()):
        if _mount_target(mount) == container_home or _mount_is_read_only(mount):
            continue
        other_source = str(_mount_source(mount) or "")
        if not other_source:
            continue
        try:
            home_is_nested = (
                os.path.commonpath([other_source, home_source]) == other_source
            )
        except ValueError:
            home_is_nested = False
        if home_is_nested:
            raise RuntimeError(
                "Host-visible container HOME source must not be inside another "
                "writable bind mount: " + other_source
            )


def _secure_directory_open_flags():
    """Return flags required for race-resistant directory traversal."""

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory:
        raise RuntimeError(
            "run_as_host_user requires no-follow directory traversal support"
        )
    return os.O_RDONLY | no_follow | directory | getattr(os, "O_CLOEXEC", 0)


def _secure_create_runtime_path(manager_root, relative_path, effective_uid):
    """Create one validated state path through directory-relative operations."""

    open_flags = _secure_directory_open_flags()
    try:
        parent_fd = os.open(manager_root, open_flags)
    except OSError as ex:
        raise RuntimeError(
            "Unable to securely open manager state root {}: {}".format(
                manager_root, ex
            )
        ) from ex
    try:
        _validate_secure_runtime_directory(
            manager_root, os.fstat(parent_fd), effective_uid
        )
        current_path = manager_root
        for component in relative_path.split(os.sep):
            current_path = os.path.join(current_path, component)
            try:
                child_fd = os.open(component, open_flags, dir_fd=parent_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=parent_fd)
                except FileExistsError:
                    pass
                except OSError as ex:
                    raise RuntimeError(
                        "Unable to securely create container HOME runtime state {}: {}".format(
                            current_path, ex
                        )
                    ) from ex
                try:
                    child_fd = os.open(component, open_flags, dir_fd=parent_fd)
                except OSError as ex:
                    raise RuntimeError(
                        "Unable to securely open container HOME runtime state {}: {}".format(
                            current_path, ex
                        )
                    ) from ex
            except OSError as ex:
                raise RuntimeError(
                    "Unable to securely open container HOME runtime state {}: {}".format(
                        current_path, ex
                    )
                ) from ex
            try:
                child_stat = os.fstat(child_fd)
            except OSError as ex:
                os.close(child_fd)
                raise RuntimeError(
                    "Unable to verify container HOME runtime state {}: {}".format(
                        current_path, ex
                    )
                ) from ex
            try:
                _validate_secure_runtime_directory(
                    current_path, child_stat, effective_uid
                )
            except RuntimeError:
                os.close(child_fd)
                raise
            os.close(parent_fd)
            parent_fd = child_fd
    finally:
        os.close(parent_fd)


def _steam_runtime_library_state(server, spec, home_relative_path):
    """Return non-secret Steam library metadata for a SteamCMD container."""

    if str(spec.get("runtime_family") or "").strip().lower() != "steamcmd-linux":
        return None
    app_id = str(server.data.get("Steam_AppID") or "").strip()
    if not app_id.isdecimal():
        return None

    install_source = server.data.get("dir")
    install_source = (
        os.path.abspath(os.path.expanduser(str(install_source)))
        if install_source
        else None
    )
    install_target = None
    if install_source:
        for mount in spec.get("mounts", ()):
            mount_source = _mount_source(mount)
            if not mount_source:
                continue
            normalized_source = os.path.abspath(
                os.path.expanduser(str(mount_source))
            )
            if normalized_source == install_source:
                install_target = posixpath.normpath(str(_mount_target(mount)))
                break
    install_target = install_target or posixpath.normpath(
        str(spec.get("working_dir") or DEFAULT_CONTAINER_WORKDIR)
    )
    install_target = install_target.replace("\\", "\\\\").replace('"', '\\"')
    relative_file = os.path.join(
        home_relative_path,
        ".steam",
        "steam",
        "steamapps",
        "libraryfolders.vdf",
    )
    content = (
        '"libraryfolders"\n'
        "{\n"
        '    "0"\n'
        "    {\n"
        f'        "path" "{install_target}"\n'
        '        "apps"\n'
        "        {\n"
        f'            "{app_id}" "0"\n'
        "        }\n"
        "    }\n"
        "}\n"
    )
    return {"relative_file": relative_file, "content": content}


def _secure_write_runtime_file(manager_root, relative_path, content, effective_uid):
    """Write one manager-owned runtime file without following symlinks."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    path = os.path.join(manager_root, relative_path)
    file_descriptor = None
    try:
        file_descriptor = os.open(path, flags, 0o600)
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_uid != effective_uid:
            raise RuntimeError(
                "Container HOME runtime state file has unsafe ownership: " + path
            )
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            file_descriptor = None
            handle.write(content)
    except OSError as ex:
        raise RuntimeError(
            "Unable to securely write container HOME runtime state {}: {}".format(
                path, ex
            )
        ) from ex
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)


def _create_host_user_container_home(plan, identity):
    """Securely create the directories approved by a prior validation plan."""

    effective_uid, _effective_gid = identity
    for relative_path in plan["relative_paths"]:
        _secure_create_runtime_path(
            plan["manager_root"], relative_path, effective_uid
        )
    for generated_file in plan.get("generated_files", ()):
        _secure_write_runtime_file(
            plan["manager_root"],
            generated_file["relative_file"],
            generated_file["content"],
            effective_uid,
        )


class ContainerRuntime(BaseRuntime):
    """Docker-backed runtime."""

    runtime_name = "docker"
    running_description = "docker container is running"
    missing_description = "no docker container"

    @staticmethod
    def _run_check_output(command, text=False):
        """Execute a Docker CLI command and return its output."""

        try:
            return sp.check_output(
                command,
                stderr=sp.STDOUT,
                shell=False,
                text=text,
            )
        except sp.CalledProcessError as ex:
            output = ex.output if isinstance(ex.output, str) else ex.output.decode(errors="replace")
            raise RuntimeError(output.strip() or "Docker command failed") from ex
        except OSError as ex:
            raise RuntimeError("Error executing docker: " + str(ex)) from ex

    def _image_exists(self, image):
        """Return whether *image* is already available locally."""

        try:
            self._run_check_output(["docker", "image", "inspect", image], text=True)
        except RuntimeError:
            return False
        return True

    def _container_running_state(self, name):
        """Return ``True``/``False`` if *name* exists, else ``None``."""

        try:
            output = self._run_check_output(
                ["docker", "inspect", "-f", "{{.State.Running}}", name],
                text=True,
            )
        except RuntimeError:
            return None
        return output.strip().lower() == "true"

    def _runtime_family_dockerfile(self, family):
        """Return the repository Dockerfile path for *family*, if available."""

        relative_path = RUNTIME_FAMILY_DOCKERFILES.get(canonicalize_runtime_family(family))
        if not relative_path:
            return None
        dockerfile_path = os.path.join(REPO_ROOT, relative_path)
        if not os.path.isfile(dockerfile_path):
            return None
        return dockerfile_path

    def _current_container_identity_mount_roots(self):
        return _current_container_identity_mount_roots()

    def _validate_mount_path_identity(self, spec):
        """Reject bind mounts that are not host-visible in manager-container mode."""

        spec["mounts"] = _resolve_host_visible_mounts(spec.get("mounts", ()))

    def docker_cli_version(self):
        """Return the local Docker client version string."""

        return self._run_check_output(
            ["docker", "version", "--format", "{{.Client.Version}}"],
            text=True,
        ).strip()

    def validate_mount_path_identity(self, spec):
        """Public wrapper for bind-mount identity validation."""

        self._validate_mount_path_identity(spec)

    def image_exists(self, image):
        """Public wrapper that reports whether an image is present locally."""

        return self._image_exists(image)

    def container_running_state(self, name):
        """Public wrapper that returns the current container running state."""

        return self._container_running_state(name)

    def _ensure_runtime_image_available(self, spec):
        """Ensure the runtime image exists locally before starting the container.

        Manager-container quick-start should keep working without GHCR auth. When
        a server still points at one of AlphaGSM's default runtime-family tags and
        that tag is not present locally, build the matching in-repo family image
        with the same tag instead of forcing a registry pull.
        """

        image = spec.get("image")
        family = canonicalize_runtime_family(spec.get("runtime_family"))
        if not image or not family:
            return
        if self._image_exists(image):
            return

        default_image = RUNTIME_FAMILY_DEFAULTS.get(family, {}).get("image")
        if image != default_image:
            return

        dockerfile_path = self._runtime_family_dockerfile(family)
        if dockerfile_path is None:
            return

        self._run_check_output(
            [
                "docker",
                "build",
                "-f",
                dockerfile_path,
                "-t",
                image,
                REPO_ROOT,
            ],
            text=True,
        )

    def start(self, server, *args, **kwargs):
        identity = None
        module_requirements = _get_module_runtime_requirements(server)
        if module_requirements.get("run_as_host_user", False):
            identity = _resolve_effective_host_user(reject_root=False)
            _validate_requirement_identity_before_spec(
                module_requirements, identity
            )
        mount_snapshot = _MountTranslationSnapshot()
        spec = get_container_spec(
            server,
            *args,
            _runtime_requirements=module_requirements,
            _mount_snapshot=mount_snapshot,
            **kwargs,
        )
        _validate_container_identity_contract(module_requirements, spec)
        home_plan = None
        if module_requirements.get("run_as_host_user", False):
            home_plan = _validate_host_user_container_home(server, spec, identity)
        snapshot_token = _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.set(mount_snapshot)
        try:
            self._validate_mount_path_identity(spec)
        finally:
            _ACTIVE_MOUNT_TRANSLATION_SNAPSHOT.reset(snapshot_token)
        if module_requirements.get("run_as_host_user", False):
            _validate_host_visible_host_user_home_overlap(spec)
        self._ensure_runtime_image_available(spec)
        container_state = self._container_running_state(spec["container_name"])
        if container_state is False:
            self._run_check_output(["docker", "rm", "-f", spec["container_name"]], text=True)
        elif container_state is True:
            raise RuntimeError("Docker container is already running: " + spec["container_name"])
        if home_plan is not None:
            _create_host_user_container_home(home_plan, identity)
        command = ["docker", "run", "-d"]
        if spec.get("stdin_open", False):
            command.append("-i")
        if spec.get("tty", False):
            command.append("-t")
        if identity is not None:
            command.extend(["--user", _format_effective_host_user(identity)])
        command.extend(["--name", spec["container_name"]])
        if spec.get("network_mode"):
            command.extend(["--network", spec["network_mode"]])
        if spec.get("working_dir"):
            command.extend(["-w", spec["working_dir"]])
        for key, value in sorted((spec.get("env") or {}).items()):
            command.extend(["-e", f"{key}={value}"])
        for mount in spec.get("mounts", ()):
            if isinstance(mount, dict):
                mode = mount.get("mode", "rw")
                mount = f"{mount['source']}:{mount['target']}:{mode}"
            command.extend(["-v", str(mount)])
        for port in spec.get("ports", ()):
            if isinstance(port, dict):
                proto = port.get("protocol", "tcp")
                port = f"{port['host']}:{port['container']}/{proto}"
            command.extend(["-p", str(port)])
        command.append(spec["image"])
        command.extend(spec.get("command", ()))
        self._run_check_output(command, text=True)

    def is_running(self, server):
        name = resolve_runtime_metadata(server).get("container_name", "alphagsm-" + server.name)
        return self._container_running_state(name) is True

    def kill(self, server):
        name = resolve_runtime_metadata(server).get("container_name", "alphagsm-" + server.name)
        try:
            self._run_check_output(["docker", "stop", "--time", "10", name], text=True)
        except RuntimeError:
            pass
        self._run_check_output(["docker", "rm", "-f", name], text=True)

    def send_input(self, server, text):
        spec = get_container_spec(server)
        stop_mode = spec.get("stop_mode", "docker-stop")
        if stop_mode != "exec-console":
            raise RuntimeError(
                "Runtime send_input is only supported for docker stop_mode=exec-console"
            )
        shell_command = "printf '%s' {} > /proc/1/fd/0".format(shlex.quote(text))
        self._run_check_output(
            ["docker", "exec", spec["container_name"], "sh", "-lc", shell_command],
            text=True,
        )

    def connect(self, server):
        spec = get_container_spec(server)
        try:
            sp.check_call(["docker", "attach", spec["container_name"]], shell=False)
        except sp.CalledProcessError as ex:
            raise RuntimeError("docker attach failed with return value: " + str(ex.returncode)) from ex
        except OSError as ex:
            raise RuntimeError("Error executing docker: " + str(ex)) from ex

    def show_logs(self, server, lines=50):
        spec = get_container_spec(server)
        result = sp.run(
            ["docker", "logs", "--tail", str(lines), spec["container_name"]],
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("Failed to read docker logs for: " + spec["container_name"])


def get_runtime(server):
    """Return the active runtime for *server*."""

    runtime_name = resolve_runtime_metadata(server).get("runtime", "process")
    if runtime_name == "docker":
        return ContainerRuntime()
    return ProcessRuntime()


def send_to_server(server, text):
    """Send console input through the active runtime."""

    return get_runtime(server).send_input(server, text)


def check_server_running(server):
    """Return whether the server is running via its selected runtime."""

    return get_runtime(server).is_running(server)


def connect_to_server(server):
    """Connect to the live server console via its selected runtime."""

    return get_runtime(server).connect(server)


def show_server_logs(server, lines=50):
    """Display recent logs for the selected runtime."""

    return get_runtime(server).show_logs(server, lines=lines)
