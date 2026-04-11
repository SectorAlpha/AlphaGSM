"""Wine/Proton integration helpers for running Windows-binary game servers on Linux.

On Linux hosts, Windows-only game server binaries can be run through Wine or
Proton-GE.  This module provides helpers to locate the available tool and to
construct a wrapped command that the screen/subprocess backend can launch
without any modifications.

Usage example in a game module::

    from utils.platform_info import IS_LINUX
    import utils.proton as proton

    def get_start_command(server):
        cmd = [server.data["exe_name"]]
        if IS_LINUX:
            cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
        return cmd, server.data["dir"]
"""

import os
import shutil

CONTAINER_SERVER_DIR = "/srv/server"
CONTAINER_WINEPREFIX_DIR = "/srv/wineprefix"
HEADLESS_ENV = {
    "DISPLAY": "",
    "WINEDLLOVERRIDES": "winex11.drv=",
}

# ---------------------------------------------------------------------------
# Proton-GE search directories (checked in order; first match wins)
# ---------------------------------------------------------------------------

_PROTON_SEARCH_DIRS = [
    os.path.expanduser("~/.local/share/proton-ge"),
    os.path.expanduser("~/.steam/root/compatibilitytools.d"),
    os.path.expanduser("~/.local/share/Steam/compatibilitytools.d"),
    "/opt/proton-ge",
]


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def find_wine():
    """Return the absolute path of the ``wine`` executable, or ``None``."""
    return shutil.which("wine")


def find_proton():
    """Return the absolute path of a Proton ``proton`` script, or ``None``.

    Searches *_PROTON_SEARCH_DIRS* for sub-directories that contain a
    ``proton`` script.  When multiple versions are present the
    lexicographically last directory name is preferred (e.g. ``GE-Proton9-27``
    is chosen over ``GE-Proton9-10``).
    """
    for search_dir in _PROTON_SEARCH_DIRS:
        if not os.path.isdir(search_dir):
            continue
        entries = sorted(
            (
                e
                for e in os.listdir(search_dir)
                if os.path.isdir(os.path.join(search_dir, e))
            ),
            reverse=True,
        )
        for entry in entries:
            proton_exe = os.path.join(search_dir, entry, "proton")
            if os.path.isfile(proton_exe):
                return proton_exe
    return None


def is_available():
    """Return ``True`` if Wine or Proton-GE is available on this system."""
    return find_wine() is not None or find_proton() is not None


# ---------------------------------------------------------------------------
# Command wrapping
# ---------------------------------------------------------------------------

def wrap_command(command, wineprefix=None, prefer_proton=False):
    """Wrap *command* so that a Windows executable runs on Linux.

    Prefers Wine when both Wine and Proton-GE are installed unless
    *prefer_proton* is ``True``.  When
    *wineprefix* is provided it is forwarded via the ``WINEPREFIX`` (Wine) or
    ``STEAM_COMPAT_DATA_PATH`` (Proton) environment variable using the
    ``env(1)`` utility, so the existing screen/subprocess backends need no
    changes.

    Args:
        command: The original command as a sequence of strings.  The first
            element must be the Windows executable name or relative path.
        wineprefix: Optional path to a Wine prefix directory or Proton
            compatibility data directory.
        prefer_proton: When ``True`` choose Proton-GE before Wine if both are
            available. Use this for Windows servers known to require Proton.

    Returns:
        A new list of strings representing the wrapped command.

    Raises:
        RuntimeError: If neither Wine nor Proton-GE is available.
    """
    # Headless Wine env vars applied to every launch:
    #   DISPLAY=             — no display; Wine uses its built-in null renderer
    #   WINEDLLOVERRIDES=winex11.drv=
    #                        — override the X11 driver with nothing, forcing the
    #                          null/headless renderer even if DISPLAY is set in
    #                          the outer environment
    # Dedicated game servers never need a display; these vars ensure Wine never
    # tries to open one regardless of the host environment.
    _HEADLESS = ["%s=%s" % (key, value) for key, value in HEADLESS_ENV.items()]

    proton = find_proton()
    wine = find_wine()

    if prefer_proton and proton is not None:
        compat_dir = wineprefix or os.path.expanduser("~/.proton")
        os.makedirs(compat_dir, exist_ok=True)
        return [
            "env",
            *_HEADLESS,
            f"STEAM_COMPAT_DATA_PATH={compat_dir}",
            "STEAM_COMPAT_CLIENT_INSTALL_PATH=",
            proton,
            "run",
        ] + list(command)

    if wine is not None:
        env_vars = list(_HEADLESS)
        if wineprefix:
            env_vars.append(f"WINEPREFIX={wineprefix}")
        return ["env"] + env_vars + [wine] + list(command)

    if proton is not None:
        compat_dir = wineprefix or os.path.expanduser("~/.proton")
        os.makedirs(compat_dir, exist_ok=True)
        return [
            "env",
            *_HEADLESS,
            f"STEAM_COMPAT_DATA_PATH={compat_dir}",
            "STEAM_COMPAT_CLIENT_INSTALL_PATH=",
            proton,
            "run",
        ] + list(command)

    raise RuntimeError(
        "Neither Wine nor Proton-GE is available on this system.  "
        "Run  scripts/install_proton.sh  to install one of them."
    )


def _is_env_assignment(token):
    """Return whether *token* looks like an ``env`` variable assignment."""

    if "=" not in token:
        return False
    key, _value = token.split("=", 1)
    return key.isidentifier()


def unwrap_runtime_command(command):
    """Strip a leading ``env``/Wine/Proton launcher wrapper from *command*."""

    command = list(command)
    if not command:
        return []
    index = 0
    if command[index] == "env":
        index += 1
        while index < len(command) and _is_env_assignment(command[index]):
            index += 1
    if index >= len(command):
        return command
    launcher = os.path.basename(command[index])
    if launcher in ("wine", "wine64"):
        return command[index + 1 :]
    if index + 1 < len(command) and command[index + 1] == "run":
        return command[index + 2 :]
    return command


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


def _resolve_container_wineprefix(server):
    """Return ``(mounts, container_wineprefix)`` for a Docker-backed server."""

    mounts = []
    server_dir = server.data.get("dir")
    if server_dir:
        mounts.append(
            {
                "source": server_dir,
                "target": CONTAINER_SERVER_DIR,
                "mode": "rw",
            }
        )
    wineprefix = server.data.get("wineprefix")
    if not wineprefix:
        return mounts, os.path.join(CONTAINER_SERVER_DIR, ".alphagsm-wineprefix")

    server_dir_abs = os.path.abspath(server_dir or "")
    wineprefix_abs = os.path.abspath(wineprefix)
    if server_dir_abs and (
        wineprefix_abs == server_dir_abs
        or wineprefix_abs.startswith(server_dir_abs.rstrip(os.sep) + os.sep)
    ):
        rel_path = os.path.relpath(wineprefix_abs, server_dir_abs)
        if rel_path == ".":
            return mounts, CONTAINER_SERVER_DIR
        return mounts, os.path.join(CONTAINER_SERVER_DIR, rel_path)

    mounts.append(
        {
            "source": wineprefix,
            "target": CONTAINER_WINEPREFIX_DIR,
            "mode": "rw",
        }
    )
    return mounts, CONTAINER_WINEPREFIX_DIR


def get_runtime_requirements(
    server,
    *,
    port_definitions=(),
    prefer_proton=False,
    extra_env=None,
):
    """Return Docker metadata for Windows servers run through Wine/Proton."""

    mounts, wineprefix = _resolve_container_wineprefix(server)
    env = dict(HEADLESS_ENV)
    env["ALPHAGSM_WINEPREFIX"] = wineprefix
    env["ALPHAGSM_PREFER_PROTON"] = "1" if prefer_proton else "0"
    if extra_env:
        env.update({key: str(value) for key, value in extra_env.items()})

    requirements = {
        "engine": "docker",
        "family": "wine-proton",
        "mounts": mounts,
        "env": env,
    }
    ports = _build_port_specs(server, port_definitions)
    if ports:
        requirements["ports"] = ports
    return requirements


def get_container_spec(
    server,
    get_start_command,
    *,
    port_definitions=(),
    prefer_proton=False,
    extra_env=None,
    working_dir=CONTAINER_SERVER_DIR,
):
    """Return the Docker launch spec for a Wine/Proton-backed server."""

    command, _cwd = _get_container_start_command(server, get_start_command)
    requirements = get_runtime_requirements(
        server,
        port_definitions=port_definitions,
        prefer_proton=prefer_proton,
        extra_env=extra_env,
    )
    return {
        "working_dir": working_dir,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "env": requirements.get("env", {}),
        "command": unwrap_runtime_command(command),
    }


def _get_container_start_command(server, get_start_command):
    """Return a start command suitable for Docker manifest generation.

    Some Windows modules build their process-runtime command by calling
    ``wrap_command`` directly, which requires Wine or Proton to be installed on
    the host. Docker manifest generation should stay host-independent, so when
    the only failure is a missing local Wine/Proton install, temporarily bypass
    the wrapper and recover the underlying executable command.
    """

    try:
        return get_start_command(server)
    except RuntimeError as exc:
        if "Neither Wine nor Proton-GE is available" not in str(exc):
            raise

    original_wrap_command = wrap_command
    try:
        globals()["wrap_command"] = lambda command, **_kwargs: list(command)
        return get_start_command(server)
    finally:
        globals()["wrap_command"] = original_wrap_command
