"""tmux process backend for AlphaGSM."""

import os
import subprocess as sp

from .backend import ProcessBackend, ProcessError


class TmuxBackend(ProcessBackend):
    """Manage server sessions through ``tmux``."""

    @property
    def backend_name(self):
        """Return ``'tmux'``."""
        return "tmux"

    def _tag(self, name):
        """Return the full tmux session name for *name*."""
        return self._session_tag + name

    # ── public API ──────────────────────────────────────────────────────────

    def start(self, name, command, cwd=None):
        """Start a detached tmux session running *command*."""
        self._ensure_log_dir()
        self._rotatelogs(name)
        tag = self._tag(name)
        cmd = ["tmux", "new-session", "-d", "-s", tag]
        if cwd is not None:
            cmd += ["-c", cwd]
        cmd += list(command)
        try:
            result = sp.check_output(cmd, stderr=sp.STDOUT, shell=False)
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "tmux new-session failed: " + ex.output.decode(),
                ex.returncode,
                ex.output,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing tmux: " + str(ex)) from ex
        # Enable logging by piping pane output to the log file.
        log_file = self.logpath(name)
        try:
            sp.check_output(
                [
                    "tmux",
                    "pipe-pane",
                    "-t",
                    tag,
                    "-o",
                    "cat >> " + log_file,
                ],
                stderr=sp.STDOUT,
                shell=False,
            )
        except (sp.CalledProcessError, OSError):
            pass  # logging is best-effort
        return result

    def send_raw(self, name, command):
        """Raw screen-style commands are not supported under tmux."""
        raise ProcessError(
            "send_raw is not supported by the tmux backend; use send_input instead"
        )

    def send_input(self, name, text):
        """Send *text* to the server process via ``tmux send-keys``."""
        tag = self._tag(name)
        # Handle bare Ctrl-C (used by many game modules for shutdown).
        if text == "\003":
            self._send_keys(tag, "C-c")
            return
        stripped = text.strip("\n")
        if not stripped:
            self._send_keys(tag, "Enter")
            return
        for line in stripped.split("\n"):
            if line:
                self._send_keys(tag, "-l", line)
            self._send_keys(tag, "Enter")

    def kill(self, name):
        """Kill the tmux session."""
        tag = self._tag(name)
        try:
            sp.check_output(
                ["tmux", "kill-session", "-t", tag],
                stderr=sp.STDOUT,
                shell=False,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "tmux kill-session failed: " + ex.output.decode(),
                ex.returncode,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing tmux: " + str(ex)) from ex

    def is_running(self, name):
        """Return whether the named tmux session exists."""
        tag = self._tag(name)
        try:
            sp.check_output(
                ["tmux", "has-session", "-t", tag],
                stderr=sp.STDOUT,
                shell=False,
            )
            return True
        except (sp.CalledProcessError, OSError):
            return False

    def connect(self, name):
        """Attach the current terminal to the named tmux session."""
        tag = self._tag(name)
        try:
            sp.check_call(
                ["tmux", "attach-session", "-t", tag],
                shell=False,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "tmux attach failed with return value: " + str(ex.returncode),
                ex.returncode,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing tmux: " + str(ex)) from ex

    def list_sessions(self):
        """Yield server names for every AlphaGSM tmux session."""
        try:
            output = sp.check_output(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                stderr=sp.STDOUT,
                shell=False,
                text=True,
            )
        except (sp.CalledProcessError, OSError):
            return
        prefix = self._session_tag
        plen = len(prefix)
        for line in output.strip().split("\n"):
            if line.startswith(prefix):
                yield line[plen:]

    # ── internal helpers ────────────────────────────────────────────────────

    def _send_keys(self, tag, *keys):
        """Run ``tmux send-keys`` with the supplied key arguments."""
        try:
            sp.check_output(
                ["tmux", "send-keys", "-t", tag] + list(keys),
                stderr=sp.STDOUT,
                shell=False,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "tmux send-keys failed: " + ex.output.decode(),
                ex.returncode,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing tmux: " + str(ex)) from ex
