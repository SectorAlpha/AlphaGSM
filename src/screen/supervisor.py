"""Persistent, authenticated loopback control for a single server process.

The supervisor owns stdin for the lifetime of the game. Requests use bounded
JSON messages, never pickle, and a random credential in an owner-only directory.
"""

import hmac
import json
import os
import queue
import threading
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from utils.state_io import state_lock

MAX_MESSAGE = 65536


def write_private_json(path, value):
    """Publish a complete owner-only JSON file on the same filesystem."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".new")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish_stopped_state(endpoint_path):
    """Retire the endpoint despite brief Windows status-reader contention."""
    stopped = {"stopped": True}
    for attempt in range(20):
        try:
            endpoint_path.unlink(missing_ok=True)
            break
        except PermissionError as error:
            # Windows cannot delete this file while another CLI reads it.
            # A retained endpoint is harmless after the listener has closed;
            # record persistent contention so the next start can clean it up.
            if attempt == 19:
                stopped["endpoint_cleanup_error"] = str(error)
            else:
                time.sleep(0.05)
    write_private_json(endpoint_path.with_name("stopped.json"), stopped)


def read_message(connection):
    """Read one newline-delimited JSON object with a strict size limit."""
    payload = bytearray()
    while b"\n" not in payload:
        block = connection.recv(min(4096, MAX_MESSAGE + 1 - len(payload)))
        if not block:
            raise ValueError("Incomplete control request")
        payload.extend(block)
        if len(payload) > MAX_MESSAGE:
            raise ValueError("Control request exceeds size limit")
    value = json.loads(payload.split(b"\n", 1)[0])
    if not isinstance(value, dict):
        raise ValueError("Control request must be an object")
    return value


def external_environment():
    """Restore library search paths before starting a non-bundled program."""
    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        for key in ("LD_LIBRARY_PATH", "LIBPATH"):
            original = env.pop(key + "_ORIG", None)
            if original is None:
                env.pop(key, None)
            else:
                env[key] = original
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetDllDirectoryW(None)
    return env


def terminate_tree(process, job=None):
    """Terminate the owned process tree, escalating after a bounded grace."""
    if job is not None:
        job.terminate()
    elif os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False, timeout=15)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        # Descendants can remain even when their parent has exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class ConsoleWriter:
    """Queue bounded input without blocking the authenticated control channel."""

    def __init__(self, pipe):
        self.pipe = pipe
        self.pending = queue.Queue(maxsize=8)
        self.error = None
        self.thread = threading.Thread(target=self._write, daemon=True)
        self.thread.start()

    def submit(self, text):
        """Accept text for delivery; reject excess input while the pipe is full."""
        if self.error is not None:
            raise OSError(self.error)
        try:
            self.pending.put_nowait(text.encode("utf-8"))
        except queue.Full as ex:
            raise ValueError("Console input queue is full; server is not reading input.") from ex

    def _write(self):
        try:
            while True:
                payload = self.pending.get()
                if payload is None:
                    return
                view = memoryview(payload)
                while view:
                    written = self.pipe.write(view)
                    if not written:
                        raise BrokenPipeError("Server console pipe is closed.")
                    view = view[written:]
        except (OSError, ValueError) as ex:
            self.error = str(ex)

    def close(self):
        """Stop the writer after the server tree has released its read handles."""
        try:
            self.pending.put_nowait(None)
        except queue.Full:
            pass
        self.thread.join(timeout=1)
        self.pipe.close()


def _stop_worker(signum, _frame):
    """Use normal cleanup when a launcher cancels a Unix supervisor."""
    raise SystemExit(128 + signum)


def serve(request_path):
    """Keep a crash-released ownership lock for the entire worker lifetime."""
    previous = None
    if os.name != "nt" and threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGTERM, _stop_worker)
    try:
        with state_lock(Path(request_path).with_name("owner"), timeout=0):
            return _serve(request_path)
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)


def _serve(request_path):
    """Start a server and service local commands until that server exits."""
    request_path = Path(request_path)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    endpoint_path = request_path.with_name("endpoint.json")
    error_path = request_path.with_name("error.json")
    process = None
    writer = None
    job = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(4)
            listener.settimeout(0.2)
            if os.name == "nt":
                from .windows_job import WindowsJob, CREATE_SUSPENDED

                job = WindowsJob()
                options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED}
            else:
                options = {"start_new_session": True}
            with open(request["log"], "a", encoding="utf-8") as log:
                process = subprocess.Popen(request["command"], cwd=request["cwd"],
                                           stdin=subprocess.PIPE, stdout=log, stderr=log, bufsize=0,
                                           env=external_environment(), **options)
                if job is not None:
                    job.attach_and_resume(process)
                writer = ConsoleWriter(process.stdin)
                write_private_json(endpoint_path, {
                    "port": listener.getsockname()[1], "token": request["token"],
                    "pid": process.pid, "supervisor_pid": os.getpid(),
                })
                while process.poll() is None:
                    try:
                        connection, _address = listener.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        connection.settimeout(2)
                        try:
                            message = read_message(connection)
                            if not hmac.compare_digest(str(message.get("token", "")).encode("utf-8"), request["token"].encode("utf-8")):
                                raise ValueError("Invalid control credential")
                            action = message.get("action")
                            if action == "input":
                                text = message["text"]
                                if not isinstance(text, str):
                                    raise ValueError("Console input must be text")
                                if text == "\003":
                                    os.kill(process.pid, signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
                                else:
                                    writer.submit(text)
                            elif action == "kill":
                                terminate_tree(process, job)
                            elif action != "ping":
                                raise ValueError("Unknown control action")
                            response = {"ok": True, "running": process.poll() is None}
                        except (OSError, ValueError, KeyError) as error:
                            response = {"ok": False, "error": str(error)}
                        try:
                            connection.sendall(json.dumps(response).encode() + b"\n")
                        except OSError:
                            pass
                process.wait()
        return 0
    except (OSError, ValueError, KeyError) as error:
        write_private_json(error_path, {"error": "Cannot start process: " + str(error)})
        return 1
    finally:
        try:
            if process is not None:
                terminate_tree(process, job)
        finally:
            if job is not None:
                job.close()
        if writer is not None:
            writer.close()
        publish_stopped_state(endpoint_path)


if __name__ == "__main__":
    sys.exit(serve(sys.argv[1]))
