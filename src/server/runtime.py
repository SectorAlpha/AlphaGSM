"""Runtime abstraction for AlphaGSM server execution.

Supports the existing process-backed runtime and an additional Docker-backed
container runtime. Game modules can describe Docker requirements via
``get_runtime_requirements(server)`` and ``get_container_spec(server)`` hooks,
but Docker is only selected when configuration opts into it.
"""

from __future__ import annotations

import copy
import os
import shlex
import subprocess as sp

import screen
from utils.settings import settings
from utils import proton


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
        "image": "ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04",
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
        "image": "ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:2026-04",
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "service-console": {
        "runtime": "docker",
        "runtime_family": "service-console",
        "image": "ghcr.io/sectoralpha/alphagsm-service-console-runtime:2026-04",
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "simple-tcp": {
        "runtime": "docker",
        "runtime_family": "simple-tcp",
        "image": "ghcr.io/sectoralpha/alphagsm-simple-tcp-runtime:2026-04",
        "network_mode": "bridge",
        "stop_mode": "docker-stop",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "steamcmd-linux": {
        "runtime": "docker",
        "runtime_family": "steamcmd-linux",
        "image": "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:2026-04",
        "network_mode": "bridge",
        "stop_mode": "exec-console",
        "env": {},
        "mounts": [],
        "ports": [],
    },
    "wine-proton": {
        "runtime": "docker",
        "runtime_family": "wine-proton",
        "image": "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:2026-04",
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


def build_container_spec(
    server,
    *,
    family,
    get_start_command,
    port_definitions=(),
    env=None,
    mounts=None,
    stdin_open=True,
    working_dir=None,
    extra=None,
):
    """Build a Docker launch spec from a module start-command hook."""

    command, cwd = get_start_command(server)
    requirements = build_runtime_requirements(
        server,
        family=family,
        port_definitions=port_definitions,
        env=env,
        mounts=mounts,
    )
    if working_dir is None:
        if requirements.get("mounts"):
            working_dir = DEFAULT_CONTAINER_WORKDIR
        else:
            working_dir = cwd
    spec = {
        "working_dir": working_dir,
        "stdin_open": stdin_open,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": list(command),
    }
    if extra:
        spec.update(copy.deepcopy(dict(extra)))
    return spec


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
    if req.get("runtime") == "docker":
        req.setdefault("container_name", "alphagsm-" + server_name)
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
        if (major, minor) < (1, 17):
            return 8
        if (major, minor) < (1, 20):
            return 17
        if (major, minor) == (1, 20) and patch < 5:
            return 17
        return 21
    return 21


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
    return merged


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

    def start(self, server, *args, **kwargs):
        spec = get_container_spec(server, *args, **kwargs)
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
        try:
            output = self._run_check_output(
                ["docker", "inspect", "-f", "{{.State.Running}}", name],
                text=True,
            )
        except RuntimeError:
            return False
        return output.strip().lower() == "true"

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
