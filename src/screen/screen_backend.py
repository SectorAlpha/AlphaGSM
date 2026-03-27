"""GNU screen process backend for AlphaGSM."""

import os
import subprocess as sp

from .backend import ProcessBackend, ProcessError


class ScreenBackend(ProcessBackend):
    """Manage server sessions through GNU ``screen``."""

    def __init__(self, session_tag, log_path, keeplogs, screenrc, template_dir):
        """Initialise with paths needed for screen configuration files."""
        from utils.platform_info import IS_WINDOWS
        if IS_WINDOWS:
            raise ProcessError(
                "The 'screen' backend is not available on Windows. "
                "Please use 'subprocess' or 'tmux' (on WSL/Linux) instead."
            )
        super().__init__(session_tag, log_path, keeplogs)
        self._screenrc = screenrc
        self._template_dir = template_dir

    @property
    def backend_name(self):
        """Return ``'screen'``."""
        return "screen"

    # ── internal helpers ────────────────────────────────────────────────────

    def _write_screenrc(self, force=False):
        """Ensure the per-user AlphaGSM screen configuration file exists."""
        dirpath = os.path.dirname(self._screenrc)
        if not os.path.isdir(dirpath):
            os.mkdir(dirpath)
        if not os.path.isfile(self._screenrc) or force:
            template = os.path.join(self._template_dir, "screenrc_template.txt")
            with open(template, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = text % os.path.join(self._log_path, "")
            with open(self._screenrc, "w", encoding="utf-8") as fh:
                fh.write(text)

    def _tag(self, name):
        """Return the full session tag for *name*."""
        return self._session_tag + name

    # ── public API ──────────────────────────────────────────────────────────

    def start(self, name, command, cwd=None):
        """Start a detached GNU screen session running *command*."""
        self._write_screenrc()
        self._ensure_log_dir()
        self._rotatelogs(name)
        extra = {}
        if cwd is not None:
            extra["cwd"] = cwd
        try:
            return sp.check_output(
                ["screen", "-dmLS", self._tag(name), "-c", self._screenrc]
                + list(command),
                stderr=sp.STDOUT,
                shell=False,
                **extra,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "Screen failed with return value: "
                + str(ex.returncode)
                + " and output: '"
                + str(ex.output)
                + "'",
                ex.returncode,
                ex.output,
            ) from ex
        except FileNotFoundError as ex:
            raise ProcessError(
                "Can't change to directory '" + str(cwd) + "' while starting screen",
                ex,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing screen: " + str(ex)) from ex

    def send_raw(self, name, command):
        """Send a raw screen command list to the named session."""
        try:
            return sp.check_output(
                ["screen", "-S", self._tag(name), "-p", "0", "-X"] + list(command),
                stderr=sp.STDOUT,
                shell=False,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "Screen failed with return value: "
                + str(ex.returncode)
                + " and output: '"
                + ex.output.decode()
                + "'",
                ex.returncode,
                ex.output,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing screen: " + str(ex)) from ex

    def send_input(self, name, text):
        """Send *text* to the server process via ``screen stuff``."""
        return self.send_raw(name, ["stuff", text])

    def kill(self, name):
        """Kill the screen session by sending the ``quit`` command."""
        return self.send_raw(name, ["quit"])

    def is_running(self, name):
        """Return whether the named screen session exists."""
        try:
            self.send_raw(name, ["select", "."])
            return True
        except ProcessError:
            return False

    def connect(self, name):
        """Attach the current terminal to the named screen session."""
        try:
            sp.check_call(
                [
                    "script",
                    "/dev/null",
                    "-c",
                    "screen -rS '" + self._tag(name) + "'",
                ],
                shell=False,
            )
        except sp.CalledProcessError as ex:
            raise ProcessError(
                "Screen Failed with return value: " + str(ex.returncode),
                ex.returncode,
            ) from ex
        except OSError as ex:
            raise ProcessError("Error executing screen: " + str(ex)) from ex

    def list_sessions(self):
        """Yield server names for every AlphaGSM screen session on this host."""
        import pwd  # pylint: disable=import-outside-toplevel
        import re  # pylint: disable=import-outside-toplevel

        curruser = pwd.getpwuid(os.getuid())[0]
        filepat = re.compile(
            r"\d+\." + re.escape(self._session_tag) + "(.*)$"
        )
        for path, _dirs, files in os.walk("/var/run/screen/"):
            user = os.path.split(path)[1]
            if user[:2] != "S-":
                continue
            user = user[2:]
            for fname in files:
                match = filepat.match(fname)
                if match is not None:
                    if user == curruser:
                        yield match.group(1)
                    else:
                        yield user + "/" + match.group(1)
