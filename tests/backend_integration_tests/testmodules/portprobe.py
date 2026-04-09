"""Tiny test-only module for cheap backend port-manager lifecycle coverage."""

import os

from server import ServerError
import server.runtime as runtime_module
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("DIR", "Install directory for the tiny listener", str),
            ArgSpec("PORT", "Primary TCP port to claim and listen on", int),
            ArgSpec("QUERYPORT", "Optional secondary TCP port to claim", int),
            ArgSpec("METRICSPORT", "Optional tertiary TCP port to claim", int),
        )
    ),
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1

_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "tcp"},
    {"key": "queryport", "protocol": "tcp"},
    {"key": "metricsport", "protocol": "tcp"},
)

_RUNTIME_SCRIPT = """#!/usr/bin/env python3
import signal
import socket
import sys
import threading
import time


STOP = threading.Event()
LISTENERS = []


def _handle_signal(_signum, _frame):
    STOP.set()


def _accept_loop(sock):
    sock.settimeout(0.2)
    while not STOP.is_set():
        try:
            conn, _addr = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        conn.close()


def _stdin_loop():
    for line in sys.stdin:
        if line.strip().lower() in ("quit", "stop", "exit"):
            STOP.set()
            break


def main():
    ports = [int(value) for value in sys.argv[1:]]
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, _handle_signal)

    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen(8)
        LISTENERS.append(sock)
        threading.Thread(target=_accept_loop, args=(sock,), daemon=True).start()

    threading.Thread(target=_stdin_loop, daemon=True).start()

    while not STOP.is_set():
        time.sleep(0.1)

    for sock in LISTENERS:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
"""


def configure(server, ask, dir=None, port=None, queryport=None, metricsport=None):
    """Store a compact port set and install location for the probe server."""

    if port is None:
        port = int(server.data.get("port", os.environ.get("ALPHAGSM_PORTPROBE_DEFAULT_PORT", 28080)))
        if ask:
            inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
            if inp:
                port = int(inp)
    if queryport is None:
        queryport = int(
            server.data.get(
                "queryport",
                os.environ.get("ALPHAGSM_PORTPROBE_DEFAULT_QUERYPORT", int(port) + 1),
            )
        )
    if metricsport is None:
        metricsport = int(
            server.data.get(
                "metricsport",
                os.environ.get("ALPHAGSM_PORTPROBE_DEFAULT_METRICSPORT", int(port) + 2),
            )
        )
    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the probe server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp

    server.data["port"] = int(port)
    server.data["queryport"] = int(queryport)
    server.data["metricsport"] = int(metricsport)
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = "portprobe_runtime.py"
    server.data.save()
    return (), {}


def install(server):
    """Write the tiny TCP listener script into the requested install dir."""

    os.makedirs(server.data["dir"], exist_ok=True)
    runtime_path = os.path.join(server.data["dir"], server.data["exe_name"])
    with open(runtime_path, "w", encoding="utf-8") as handle:
        handle.write(_RUNTIME_SCRIPT)
    os.chmod(runtime_path, 0o755)


def _runtime_command(server):
    """Return the runtime command and working dir without install-time checks."""

    return (
        [
            "python3",
            "./" + server.data["exe_name"],
            str(server.data["port"]),
            str(server.data["queryport"]),
            str(server.data["metricsport"]),
        ],
        server.data["dir"],
    )


def get_start_command(server):
    """Launch the tiny Python listener on each claimed TCP port."""

    runtime_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(runtime_path):
        raise ServerError("Executable file not found")
    return _runtime_command(server)


def do_stop(server, _j):
    """Stop the listener over stdin for both process and Docker runtimes."""

    runtime_module.send_to_server(server, "quit\n")


def status(server, verbose):
    """Print a short status line that includes the claimed port set."""

    print(
        "Portprobe server on port={port} queryport={queryport} metricsport={metricsport}".format(
            **server.data
        )
    )
    if verbose > 1:
        print("Install dir:", server.data["dir"])


def message(server, msg):
    """No-op generic message hook for completeness."""

    print("Portprobe received message request:", msg)


def backup(server, profile=None):
    """This test-only module has no backup surface."""

    print("Portprobe backup not implemented", profile)


def checkvalue(server, key, *value):
    """Validate supported datastore edits for the probe module."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "metricsport"):
        return int(value[0])
    if key[0] in ("dir", "exe_name", "image"):
        return str(value[0])
    raise ServerError("Unsupported key")


def get_query_address(server):
    """Query the main listener over TCP reachability."""

    return ("127.0.0.1", int(server.data["port"]), "tcp")


def get_info_address(server):
    """Info uses the same lightweight TCP reachability check as query."""

    return ("127.0.0.1", int(server.data["port"]), "tcp")


def get_runtime_requirements(server):
    """Describe the explicit Docker runtime metadata for the probe server."""

    return runtime_module.build_runtime_requirements(
        server,
        family="simple-tcp",
        port_definitions=_PORT_DEFINITIONS,
        extra={"stop_mode": "exec-console"},
    )


def get_container_spec(server):
    """Describe the container launch spec for the probe server."""

    command, _cwd = _runtime_command(server)
    requirements = runtime_module.build_runtime_requirements(
        server,
        family="simple-tcp",
        port_definitions=_PORT_DEFINITIONS,
        extra={"stop_mode": "exec-console"},
    )
    return {
        "working_dir": runtime_module.DEFAULT_CONTAINER_WORKDIR,
        "stdin_open": True,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": list(command),
        "stop_mode": "exec-console",
    }
