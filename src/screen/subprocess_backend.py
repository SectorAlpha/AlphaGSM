"""Pure-Python subprocess process backend for AlphaGSM.

This backend requires no external multiplexer (no ``screen``, no ``tmux``).
It is the automatic fallback when neither is available.

Limitations compared to screen / tmux:

* ``send_input`` only works within the **same** Python process that called
  ``start``.  For cross-invocation stop commands, ``kill`` sends SIGTERM.
* ``connect`` tails the log file rather than providing an interactive shell.
"""

import os
import signal
import subprocess as sp

from utils.platform_info import IS_WINDOWS
from .backend import ProcessBackend, ProcessError

# Module-level registry of Popen objects started in *this* invocation.
_processes = {}


class SubprocessBackend(ProcessBackend):
    """Manage server sessions as plain OS sub-processes with PID-file tracking."""

    @property
    def backend_name(self):
        """Return ``'subprocess'``."""
        return "subprocess"

    # ── internal helpers ────────────────────────────────────────────────────

    def _pidfile(self, name):
        """Return the PID-file path for *name*."""
        return os.path.join(
            self._log_path, self._session_tag + name + ".pid"
        )

    def _read_pid(self, name):
        """Read and return the stored PID, or *None* if unavailable."""
        pidfile = self._pidfile(name)
        if not os.path.isfile(pidfile):
            return None
        try:
            with open(pidfile, "r", encoding="utf-8") as fh:
                return int(fh.read().strip())
        except (ValueError, OSError):
            return None

    def _cleanup_pidfile(self, name):
        """Remove a stale PID file."""
        pidfile = self._pidfile(name)
        if os.path.isfile(pidfile):
            os.remove(pidfile)

    # ── public API ──────────────────────────────────────────────────────────

    def start(self, name, command, cwd=None):
        """Start a detached subprocess and record its PID."""
        if self.is_running(name):
            raise ProcessError("Session '%s' is already running" % name)
        self._ensure_log_dir()
        self._rotatelogs(name)
        log_file = self.logpath(name)
        logfh = open(log_file, "a", encoding="utf-8")  # pylint: disable=consider-using-with
        popen_kwargs = {
            "cwd": cwd,
            "stdout": logfh,
            "stderr": logfh,
            "stdin": sp.PIPE,
        }
        if IS_WINDOWS:
            popen_kwargs["creationflags"] = sp.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        try:
            proc = sp.Popen(list(command), **popen_kwargs)
        except FileNotFoundError as ex:
            logfh.close()
            raise ProcessError("Can't start process: " + str(ex)) from ex
        except OSError as ex:
            logfh.close()
            raise ProcessError("Error starting process: " + str(ex)) from ex
        _processes[name] = (proc, logfh)
        with open(self._pidfile(name), "w", encoding="utf-8") as fh:
            fh.write(str(proc.pid))

    def send_raw(self, name, command):
        """Raw backend commands are not supported for plain sub-processes."""
        raise ProcessError(
            "send_raw is not supported by the subprocess backend"
        )

    def send_input(self, name, text):
        """Write *text* to the running process's stdin pipe.

        If the process was started by a different invocation the stdin pipe is
        not available.  For bare Ctrl-C (``\\003``), SIGINT is sent instead.
        """
        entry = _processes.get(name)
        # Ctrl-C: prefer os.kill so it works even without stdin.
        if text == "\003":
            pid = entry[0].pid if entry else self._read_pid(name)
            if pid is not None:
                try:
                    if IS_WINDOWS:
                        os.kill(pid, signal.CTRL_BREAK_EVENT)
                    else:
                        os.kill(pid, signal.SIGINT)
                    return
                except ProcessLookupError as ex:
                    raise ProcessError(
                        "Process '%s' is not running" % name
                    ) from ex
            raise ProcessError("Cannot send SIGINT to '%s': unknown PID" % name)
        if entry is None:
            raise ProcessError(
                "Cannot send input to '%s': process was started by another "
                "invocation or is not running.  Use screen or tmux for "
                "interactive server control." % name
            )
        proc, _ = entry
        if proc.stdin is None or proc.stdin.closed:
            raise ProcessError("stdin pipe for '%s' is closed" % name)
        try:
            proc.stdin.write(text.encode())
            proc.stdin.flush()
        except OSError as ex:
            raise ProcessError(
                "Error writing to stdin of '%s': %s" % (name, ex)
            ) from ex

    def kill(self, name):
        """Terminate the process, falling back to SIGKILL after a timeout."""
        entry = _processes.get(name)
        if entry is not None:
            proc, logfh = entry
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except sp.TimeoutExpired:
                proc.kill()
            logfh.close()
            del _processes[name]
            self._cleanup_pidfile(name)
            return
        # Cross-invocation: try by PID file.
        pid = self._read_pid(name)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self._cleanup_pidfile(name)
            return
        raise ProcessError("No running session '%s' to kill" % name)

    def _is_pid_alive(self, pid):
        """Return whether a process with the given PID is still running."""
        if IS_WINDOWS:
            try:
                # On Windows os.kill(pid, 0) terminates the process,
                # so we use the ctypes-free approach via tasklist.
                result = sp.run(
                    ["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                return str(pid) in result.stdout
            except OSError:
                return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def is_running(self, name):
        """Return whether the named session is still alive."""
        entry = _processes.get(name)
        if entry is not None:
            proc, logfh = entry
            if proc.poll() is None:
                return True
            # Finished – tidy up.
            logfh.close()
            del _processes[name]
            self._cleanup_pidfile(name)
            return False
        pid = self._read_pid(name)
        if pid is None:
            return False
        if self._is_pid_alive(pid):
            return True
        self._cleanup_pidfile(name)
        return False

    def connect(self, name):
        """Tail the server log file (Ctrl-C to detach)."""
        log_file = self.logpath(name)
        if not os.path.isfile(log_file):
            raise ProcessError("No log file found for '%s'" % name)
        print("Subprocess backend: tailing log (press Ctrl-C to detach)")
        if IS_WINDOWS:
            self._tail_log_python(log_file)
        else:
            try:
                sp.check_call(["tail", "-f", log_file], shell=False)
            except KeyboardInterrupt:
                pass
            except OSError as ex:
                raise ProcessError(
                    "Error tailing log for '%s': %s" % (name, ex)
                ) from ex

    @staticmethod
    def _tail_log_python(log_file):
        """Pure-Python fallback for tailing a log file on Windows."""
        import time  # pylint: disable=import-outside-toplevel
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(0, 2)  # seek to end
                while True:
                    line = fh.readline()
                    if line:
                        print(line, end="")
                    else:
                        time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    def list_sessions(self):
        """Yield server names whose PID files point to a live process."""
        if not os.path.isdir(self._log_path):
            return
        prefix = self._session_tag
        suffix = ".pid"
        plen, slen = len(prefix), len(suffix)
        for entry in os.listdir(self._log_path):
            if entry.startswith(prefix) and entry.endswith(suffix):
                name = entry[plen:-slen]
                if self.is_running(name):
                    yield name
