"""Process backend with persistent console control across CLI invocations."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

from utils.state_io import state_lock

from .backend import ProcessError
from .subprocess_backend import SubprocessBackend
from .supervisor import MAX_MESSAGE, read_message, write_private_json


def helper_launch_options():
    """Give Windows workers their own hidden console for later CTRL_BREAK input."""
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        return {"creationflags": subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP,
                "startupinfo": startup}
    return {"start_new_session": True}


class ManagedSubprocessBackend(SubprocessBackend):
    """Keep a separate supervisor alive to own each game server's stdin."""

    def _session_path(self, name):
        identity = hashlib.sha256((self._session_tag + name).encode()).hexdigest()
        return Path(self._log_path) / (".session-" + identity)

    def _request(self, name, action, **values):
        try:
            endpoint = json.loads((self._session_path(name) / "endpoint.json").read_text(encoding="utf-8"))
            payload = json.dumps({"token": endpoint["token"], "action": action, **values}).encode() + b"\n"
            if len(payload) > MAX_MESSAGE:
                raise ProcessError("Console request exceeds size limit")
            with socket.create_connection(("127.0.0.1", endpoint["port"]), timeout=2) as connection:
                connection.settimeout(20 if action == "kill" else 3)
                connection.sendall(payload)
                response = read_message(connection)
            if not response.get("ok"):
                raise ProcessError(response.get("error", "Supervisor rejected request"))
            return response
        except (OSError, ValueError, KeyError) as error:
            raise ProcessError("Cannot contact server supervisor: " + str(error)) from error

    def start(self, name, command, cwd=None):
        self._ensure_log_dir()
        try:
            with state_lock(self._session_path(name), timeout=0):
                return self._start_locked(name, command, cwd)
        except (OSError, ValueError) as error:
            raise ProcessError("Cannot start supervisor: " + str(error)) from error

    def _remove_stale_session(self, session):
        if not session.exists():
            return
        try:
            with state_lock(session / "owner", timeout=0):
                endpoint_path = session / "endpoint.json"
                if endpoint_path.exists():
                    endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
                    if self._is_pid_alive(endpoint["pid"]):
                        raise ProcessError("Supervisor is unavailable but its server may still be running; inspect its logs.")
            shutil.rmtree(session)
        except TimeoutError as error:
            raise ProcessError("Server supervisor is already starting or running") from error

    def _start_locked(self, name, command, cwd):
        if self.is_running(name):
            raise ProcessError("Session '%s' is already running" % name)
        session = self._session_path(name)
        self._remove_stale_session(session)
        session.mkdir(mode=0o700)
        helper = None
        try:
            self._rotatelogs(name)
            request_path = session / "request.json"
            write_private_json(request_path, {"command": list(command), "cwd": os.path.abspath(cwd or os.getcwd()),
                                             "log": os.path.abspath(self.logpath(name)), "token": secrets.token_hex(32),
                                             "name": name})
            env = os.environ.copy()
            if getattr(sys, "frozen", False):
                launch = [sys.executable, "--_supervise-process", str(request_path.resolve())]
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
            else:
                launch = [sys.executable, "-m", "screen.supervisor", str(request_path.resolve())]
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            options = helper_launch_options()
            with open(self.logpath(name), "a", encoding="utf-8") as log:
                helper = subprocess.Popen(launch, stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env, **options)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if (session / "endpoint.json").exists() and self.is_running(name):
                    return
                if helper.poll() is not None or (session / "error.json").exists():
                    error_path = session / "error.json"
                    message = json.loads(error_path.read_text())["error"] if error_path.exists() else "Cannot start supervisor"
                    raise ProcessError(message)
                time.sleep(0.05)
            raise ProcessError("Timed out starting server supervisor")
        except BaseException:
            if helper is None:
                shutil.rmtree(session)
            else:
                if helper.poll() is None:
                    helper.terminate()
                    try:
                        helper.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        helper.kill()
                        helper.wait(timeout=5)
                # A crashed worker may leave a live child; retain its evidence.
                try:
                    self._remove_stale_session(session)
                except (ProcessError, OSError, ValueError, KeyError):
                    pass
            raise

    def send_input(self, name, text):
        if not self._session_path(name).exists():
            return super().send_input(name, text)
        self._request(name, "input", text=text)
        return None

    def is_running(self, name):
        if not self._session_path(name).exists():
            return super().is_running(name)
        try:
            return bool(self._request(name, "ping")["running"])
        except ProcessError:
            return False

    def kill(self, name):
        session = self._session_path(name)
        try:
            with state_lock(session, timeout=5):
                if not session.exists():
                    return super().kill(name)
                self._request(name, "kill")
                with state_lock(session / "owner", timeout=5):
                    pass
                shutil.rmtree(session)
        except OSError as error:
            raise ProcessError("Supervisor did not finish shutdown: " + str(error)) from error
        return None

    def list_sessions(self):
        directory = Path(self._log_path)
        seen = set()
        if directory.exists():
            for request_path in directory.glob(".session-*/request.json"):
                try:
                    name = json.loads(request_path.read_text(encoding="utf-8"))["name"]
                    if name not in seen and self.is_running(name):
                        seen.add(name)
                        yield name
                except (OSError, ValueError, KeyError):
                    continue
        for name in super().list_sessions():
            if name not in seen:
                seen.add(name)
                yield name
