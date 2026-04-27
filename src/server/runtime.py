"""Runtime abstraction for AlphaGSM server execution.

Supports the existing process-backed runtime and an additional Docker-backed
container runtime. Game modules can describe Docker requirements via
``get_runtime_requirements(server)`` and ``get_container_spec(server)`` hooks,
but Docker is only selected when configuration opts into it.
"""

# pylint: disable=too-many-lines

from __future__ import annotations

import copy
import json
import os
import shlex
import subprocess as sp

import screen
from utils.settings import settings
from utils import proton


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_IMAGE_REGISTRY = "ghcr.io/sectoralpha"
DEFAULT_IMAGE_TAG = "latest"


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
        "stop_mode": "exec-console",
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


def _build_port_specs(server, port_definitions):
    """Return Docker port mappings for the requested server data keys."""

    ports = []
    for definition in port_definitions or ():
        if isinstance(definition, dict):
            key = definition.get("key")
            if key not in server.data or server.data[key] is None:
                continue
            ports.append(
                {
                    "host": int(server.data[key]),
                    "container": int(definition.get("container", server.data[key])),
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
    requirements = {
        "engine": "docker",
        "family": family,
    }
    if mounts is None and "dir" in server.data:
        mounts = [
            {
                "source": server.data["dir"],
                "target": DEFAULT_CONTAINER_WORKDIR,
                "mode": "rw",
            }
        ]
    if mounts:
        requirements["mounts"] = copy.deepcopy(list(mounts))
    ports = _build_port_specs(server, port_definitions)
    if ports:
        requirements["ports"] = ports
    if env:
        requirements["env"] = dict(env)
    if extra:
        requirements.update(copy.deepcopy(dict(extra)))
    return requirements


def _current_container_identity_mount_roots():
    """Return same-path bind-mount roots when AlphaGSM runs inside Docker."""

    if not os.path.exists("/.dockerenv"):
        return []

    container_name = os.environ.get("HOSTNAME", "").strip()
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

    roots = []
    for mount in mounts:
        if mount.get("Type") != "bind":
            continue
        source = str(mount.get("Source") or "").rstrip(os.sep)
        destination = str(mount.get("Destination") or "").rstrip(os.sep)
        if not source or not destination:
            continue
        if source != destination:
            continue
        roots.append(destination or os.sep)
    return roots


def validate_mount_path_identity(mounts):
    """Reject bind mounts that are not host-visible in manager-container mode."""

    identity_roots = _current_container_identity_mount_roots()
    if not identity_roots:
        return

    for mount in mounts or ():
        if isinstance(mount, dict):
            source = mount.get("source")
        else:
            source = str(mount).split(":", 1)[0]
        if not source:
            continue
        source = os.path.abspath(str(source))
        if any(
            source == root or source.startswith(root.rstrip(os.sep) + os.sep)
            for root in identity_roots
        ):
            continue
        raise RuntimeError(
            "Docker-backed server paths must live under a same-path host mount "
            "when AlphaGSM runs inside Docker. Path not visible to the host "
            "daemon: %s. Use a path under ALPHAGSM_HOME instead." % (source,)
        )


def default_install_dir(server):
    """Return the default install directory for *server*.

    Traditional host installs keep using ``~/server-name``. When AlphaGSM runs
    inside the optional manager container, that default is wrong for
    Docker-backed servers because ``/root/<name>`` only exists inside the
    manager. In that mode, prefer the shared same-path mount root and place new
    installs under ``<ALPHAGSM_HOME>/servers/<name>``.
    """

    shared_root = os.environ.get("ALPHAGSM_HOME", "").strip()
    if not shared_root and _current_container_identity_mount_roots():
        config_location = os.environ.get("ALPHAGSM_CONFIG_LOCATION", "").strip()
        if config_location:
            shared_root = os.path.dirname(os.path.abspath(os.path.expanduser(config_location)))
        if not shared_root:
            alphagsm_path = os.path.abspath(
                os.path.expanduser(
                    settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm")
                )
            )
            if os.path.basename(alphagsm_path.rstrip(os.sep)) == "home":
                shared_root = os.path.dirname(alphagsm_path)

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
):
    """Build a Docker launch spec from a module start-command hook."""

    requirements = build_runtime_requirements(
        server,
        family=family,
        port_definitions=port_definitions,
        env=env,
        mounts=mounts,
    )
    validate_mount_path_identity(requirements.get("mounts", []))
    command, cwd = get_start_command(server)
    if working_dir is None:
        if requirements.get("mounts"):
            working_dir = DEFAULT_CONTAINER_WORKDIR
        else:
            working_dir = cwd
    spec = {
        "working_dir": working_dir,
        "stdin_open": stdin_open,
        "tty": tty,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": list(command),
    }
    if extra:
        spec.update(copy.deepcopy(dict(extra)))
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


def _add_external_executable_mounts(server, mounts):
    """Ensure container mounts include symlink targets used by the executable.

    AlphaGSM often symlinks downloaded payloads from the server directory into the
    shared download cache. Docker runtime mounts only the server directory by
    default, so those symlinks become broken inside the container unless the
    target path is also mounted.
    """

    server_dir = server.data.get("dir")
    exe_name = server.data.get("exe_name")
    if not server_dir or not exe_name:
        return mounts

    exe_path = os.path.join(server_dir, exe_name)
    if not os.path.islink(exe_path):
        return mounts

    target_path = os.path.realpath(exe_path)
    server_root = os.path.abspath(server_dir)
    try:
        if os.path.commonpath([server_root, target_path]) == server_root:
            return mounts
    except ValueError:
        return mounts

    if any(_mount_covers_path(mount, target_path) for mount in mounts):
        return mounts

    mounts.append(
        {
            "source": os.path.dirname(target_path),
            "target": os.path.dirname(target_path),
            "mode": "ro",
        }
    )
    return mounts


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
    if "engine" in req and "runtime" not in req:
        req["runtime"] = req.pop("engine")
    if "family" in req and "runtime_family" not in req:
        req["runtime_family"] = req.pop("family")
    if "runtime_family" in req:
        req["runtime_family"] = canonicalize_runtime_family(req["runtime_family"])
    if "java" in req and "java_major" not in req:
        req["java_major"] = req.pop("java")
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


def resolve_runtime_metadata(server):
    """Resolve the effective runtime metadata for *server*."""

    existing = _existing_runtime_metadata(server)
    module = getattr(server, "module", None)
    if module is not None:
        ensure_runtime_hooks(module)
    hook = _get_module_hook(module, "get_runtime_requirements") if module is not None else None
    requirements = normalize_runtime_requirements(
        hook(server) if hook is not None else infer_runtime_requirements(server, module=module),
        server.name,
    )
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
    """Return the first non-empty network *field* from ``docker inspect``."""

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
        if line:
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
    if explicit_host and explicit_host not in {"0.0.0.0", "::"}:
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


def get_container_spec(server, *args, **kwargs):
    """Return the effective container spec for *server*."""

    module = getattr(server, "module", None)
    if module is not None:
        ensure_runtime_hooks(module)
    hook = _get_module_hook(module, "get_container_spec") if module is not None else None
    if hook is not None:
        spec = hook(server, *args, **kwargs) or {}
    else:
        spec = infer_container_spec(server, module=module, *args, **kwargs)
    merged = resolve_runtime_metadata(server)
    merged.update(spec)
    merged.setdefault("container_name", "alphagsm-" + server.name)
    merged.setdefault("env", {})
    merged.setdefault("mounts", [])
    merged.setdefault("ports", [])
    merged["mounts"] = _add_external_executable_mounts(
        server, list(merged.get("mounts") or [])
    )
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
        metadata = resolve_runtime_metadata(server)
    except Exception as ex:  # pragma: no cover - defensive diagnostics path
        report["runtime_resolution_error"] = str(ex)
        return report

    runtime_name = metadata.get("runtime", "process")
    report["resolved_runtime"] = runtime_name
    report["running"] = get_runtime(server).is_running(server)

    if runtime_name != "docker":
        return report

    report["runtime_family"] = metadata.get("runtime_family", "unknown")
    report["image"] = metadata.get("image", "")
    report["container_name"] = metadata.get("container_name", "")
    report["network_mode"] = metadata.get("network_mode", "")
    report["stop_mode"] = metadata.get("stop_mode", "")

    try:
        spec = get_container_spec(server)
    except Exception as ex:  # pragma: no cover - defensive diagnostics path
        report["container_spec_error"] = str(ex)
        return report

    report["mount_count"] = len(spec.get("mounts") or ())
    report["port_count"] = len(spec.get("ports") or ())

    runtime = ContainerRuntime()
    try:
        docker_cli = runtime._run_check_output(
            ["docker", "version", "--format", "{{.Client.Version}}"],
            text=True,
        ).strip()
        report["docker_cli"] = docker_cli or "ok"
    except RuntimeError as ex:
        report["docker_cli_error"] = str(ex)
        return report

    try:
        runtime._validate_mount_path_identity(spec)
        report["mount_path_identity"] = "ok"
    except RuntimeError as ex:
        report["mount_path_identity_error"] = str(ex)

    image = spec.get("image")
    if image:
        report["image_present"] = runtime._image_exists(image)

    container_name = spec.get("container_name")
    if container_name:
        container_state = runtime._container_running_state(container_name)
        if container_state is True:
            report["container_state"] = "running"
        elif container_state is False:
            report["container_state"] = "stopped"
        else:
            report["container_state"] = "missing"

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

        validate_mount_path_identity(spec.get("mounts", ()))

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
        spec = get_container_spec(server, *args, **kwargs)
        self._validate_mount_path_identity(spec)
        self._ensure_runtime_image_available(spec)
        container_state = self._container_running_state(spec["container_name"])
        if container_state is False:
            self._run_check_output(["docker", "rm", "-f", spec["container_name"]], text=True)
        elif container_state is True:
            raise RuntimeError("Docker container is already running: " + spec["container_name"])
        command = ["docker", "run", "-d"]
        if spec.get("stdin_open", False):
            command.append("-i")
        if spec.get("tty", False):
            command.append("-t")
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
