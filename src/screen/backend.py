"""Abstract process backend interface for AlphaGSM server session management.

All concrete backends (screen, tmux, subprocess) implement this interface so
that the rest of AlphaGSM can manage server processes without caring which
multiplexer or process launcher is in use.
"""

import os
from abc import ABC, abstractmethod


class ProcessError(Exception):
    """Raised when a process management operation cannot be completed."""


class ProcessBackend(ABC):
    """Abstract base defining the operations every process backend must support."""

    def __init__(self, session_tag, log_path, keeplogs):
        """Store the shared session-tag, log-path, and keeplogs settings."""
        self._session_tag = session_tag
        self._log_path = os.path.expanduser(log_path)
        self._keeplogs = keeplogs

    # ── identity ────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def backend_name(self):
        """Return the human-readable name of this backend (e.g. 'screen')."""

    # ── lifecycle ───────────────────────────────────────────────────────────

    @abstractmethod
    def start(self, name, command, cwd=None):
        """Start a detached server process under *name*."""

    @abstractmethod
    def send_input(self, name, text):
        """Send *text* to the stdin of the running server."""

    @abstractmethod
    def send_raw(self, name, command):
        """Send a backend-specific raw command list to the session."""

    @abstractmethod
    def kill(self, name):
        """Forcefully terminate the named session."""

    @abstractmethod
    def is_running(self, name):
        """Return whether the named server session is alive."""

    @abstractmethod
    def connect(self, name):
        """Attach the current terminal to the named session."""

    @abstractmethod
    def list_sessions(self):
        """Yield the plain server names of every AlphaGSM session on this host."""

    # ── logging (shared) ────────────────────────────────────────────────────

    def logpath(self, name):
        """Return the log-file path for *name*."""
        return os.path.join(self._log_path, self._session_tag + name + ".log")

    def _ensure_log_dir(self):
        """Create the log directory if it does not exist."""
        os.makedirs(self._log_path, exist_ok=True)

    def _rotatelogs(self, name):
        """Rotate log files for *name*, keeping only *keeplogs* copies."""
        logname = self._session_tag + name + ".log"
        current = os.path.join(self._log_path, logname)
        if not os.path.exists(current):
            return
        prefix = logname + "."
        plen = len(prefix)
        logs = [
            (int(entry[plen:]), entry)
            for entry in os.listdir(self._log_path)
            if entry[:plen] == prefix and entry[plen:].isdigit()
        ]
        logs.sort()
        logs = [(i, 1 if i == j else 0, f) for j, (i, f) in enumerate(logs)]
        for _i, _j, fname in ((i, j, f) for i, j, f in logs if i + j >= self._keeplogs):
            os.remove(os.path.join(self._log_path, fname))
        to_shift = [(i, f) for i, j, f in logs if j == 1 and i + j < self._keeplogs]
        for idx, fname in reversed(to_shift):
            os.rename(
                os.path.join(self._log_path, fname),
                os.path.join(self._log_path, prefix + str(idx + 1)),
            )
        os.rename(current, os.path.join(self._log_path, logname + ".0"))
