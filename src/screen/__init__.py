"""Process management layer for AlphaGSM server sessions.

Supports GNU screen, tmux, and a pure-Python subprocess fallback.
The active backend is chosen from ``alphagsm.conf`` (``[process]`` section)
or auto-detected at first use.  The public function names are unchanged so
that existing game modules keep working without modification.
"""

import os
import shutil

from .backend import ProcessError
from .tail import *  # noqa: F401,F403

# Backward-compatible alias – existing code catches ``ScreenError``.
ScreenError = ProcessError

# ── lazy backend singleton ──────────────────────────────────────────────────

_backend = None


def _read_settings():
    """Return (session_tag, log_path, keeplogs, alphagsm_path, backend_pref)."""
    from utils.settings import settings  # pylint: disable=import-outside-toplevel

    sys_screen = settings.system.getsection("screen")
    usr_screen = settings.user.getsection("screen")
    usr_core = settings.user.getsection("core")
    usr_process = settings.user.getsection("process")

    session_tag = sys_screen.get("sessiontag", "AlphaGSM#")
    alphagsm_path = usr_core.get("alphagsm_path", "~/.alphagsm")
    log_path = usr_screen.get(
        "screenlog_path",
        os.path.join(alphagsm_path, "logs"),
    )
    try:
        keeplogs = int(usr_screen.get("keeplogs", 5))
    except (ValueError, TypeError):
        keeplogs = 5
    backend_pref = usr_process.get("backend", "auto")
    return session_tag, log_path, keeplogs, alphagsm_path, backend_pref


def _detect_backend():
    """Return the name of the best backend available on this system."""
    if shutil.which("screen"):
        return "screen"
    if shutil.which("tmux"):
        return "tmux"
    return "subprocess"


def _create_backend():
    """Instantiate the configured (or auto-detected) process backend."""
    session_tag, log_path, keeplogs, alphagsm_path, pref = _read_settings()
    choice = _detect_backend() if pref == "auto" else pref

    if choice == "screen":
        from .screen_backend import ScreenBackend  # pylint: disable=import-outside-toplevel

        screenrc = os.path.join(
            os.path.expanduser(alphagsm_path), "screenrc"
        )
        template_dir = os.path.dirname(os.path.abspath(__file__))
        return ScreenBackend(session_tag, log_path, keeplogs, screenrc, template_dir)

    if choice == "tmux":
        from .tmux_backend import TmuxBackend  # pylint: disable=import-outside-toplevel

        return TmuxBackend(session_tag, log_path, keeplogs)

    if choice == "subprocess":
        from .subprocess_backend import SubprocessBackend  # pylint: disable=import-outside-toplevel

        return SubprocessBackend(session_tag, log_path, keeplogs)

    raise ProcessError("Unknown process backend: '%s'" % choice)


def _get_backend():
    """Return the active backend, creating it on first access."""
    global _backend  # pylint: disable=global-statement
    if _backend is None:
        _backend = _create_backend()
    return _backend


def get_backend():
    """Return the active :class:`ProcessBackend` instance."""
    return _get_backend()


# ── backward-compatible public API ──────────────────────────────────────────


def start_screen(name, command, cwd=None):
    """Start a detached server process."""
    return _get_backend().start(name, command, cwd=cwd)


def send_to_screen(name, command):
    """Send a raw command list to the session.

    For the screen backend this sends literal screen commands.
    For other backends the ``["quit"]`` pattern is mapped to ``kill``.
    """
    backend = _get_backend()
    if command == ["quit"]:
        return backend.kill(name)
    return backend.send_raw(name, command)


def send_to_server(name, inp):
    """Send text input to the server process."""
    return _get_backend().send_input(name, inp)


def check_screen_exists(name):
    """Return whether the named server session is currently running."""
    return _get_backend().is_running(name)


def connect_to_screen(name):
    """Attach the current terminal to the server session."""
    return _get_backend().connect(name)


def list_all_screens():
    """Yield the names of all AlphaGSM sessions on this host."""
    yield from _get_backend().list_sessions()


def logpath(name):
    """Return the log file path for a named server."""
    return _get_backend().logpath(name)


__all__ = [
    "ScreenError",
    "ProcessError",
    "start_screen",
    "send_to_screen",
    "send_to_server",
    "check_screen_exists",
    "connect_to_screen",
    "list_all_screens",
    "logpath",
    "get_backend",
]
