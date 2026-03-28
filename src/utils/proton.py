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

def wrap_command(command, wineprefix=None):
    """Wrap *command* so that a Windows executable runs on Linux.

    Prefers Wine when both Wine and Proton-GE are installed.  When
    *wineprefix* is provided it is forwarded via the ``WINEPREFIX`` (Wine) or
    ``STEAM_COMPAT_DATA_PATH`` (Proton) environment variable using the
    ``env(1)`` utility, so the existing screen/subprocess backends need no
    changes.

    Args:
        command: The original command as a sequence of strings.  The first
            element must be the Windows executable name or relative path.
        wineprefix: Optional path to a Wine prefix directory or Proton
            compatibility data directory.

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
    _HEADLESS = [
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
    ]

    wine = find_wine()
    if wine is not None:
        env_vars = list(_HEADLESS)
        if wineprefix:
            env_vars.append(f"WINEPREFIX={wineprefix}")
        return ["env"] + env_vars + [wine] + list(command)

    proton = find_proton()
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
