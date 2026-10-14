"""Authenticated native ARK Blueprint-property proof shared by CI and smoke."""

import argparse
from pathlib import Path
import re
import secrets
import sys
import time


NATIVE_COMMAND = "getall PrimalGameData_BP_Spoilers_C ModName SHOWDEFAULTS"
OBJECT_ROW = re.compile(
    r"^(?:\[[^\]\r\n]+\]\[\s*\d+\])?(?:LogObj:\s*(?:Log:\s*)?)?\s*\d+\)\s*"
    r"PrimalGameData_BP_Spoilers_C\s+"
    r"/Game/Mods/[^\s]*PrimalGameData_BP_Spoilers\."
    r"(?:Default__)?PrimalGameData_BP_Spoilers_C(?:_\d+)?\.ModName\s*=\s*"
    r'[^\r\n]*spoiler[^\r\n]*$', re.MULTILINE | re.IGNORECASE,
)


def assert_native_object_property(output):
    """Require a native object/property record; receipts, echoes and errors fail."""
    assert OBJECT_ROW.search(output), (
        "ARK did not enumerate the Meat Spoiler native Blueprint ModName property:\n"
        + output[-12000:])


def prepare_probe(server):
    """Enable disposable local RCON without passing its password in shell arguments."""
    # Imported only when executed, so parser regressions need no server runtime.
    from scripts.select_test_port import pick_free_port_group

    excluded = {int(server.data[key]) for key in ("port", "queryport")}
    excluded.add(int(server.data["port"]) + 1)
    port = pick_free_port_group(1)
    while port in excluded:
        port = pick_free_port_group(1)
    server.doset("adminpassword", secrets.token_hex(24))
    server.doset("rconport", str(port))
    server.doset("rconenabled", "true")


def probe_native_object(server, timeout=120, *, command=None, read_logs=None,
                        clock=time.monotonic, sleep=time.sleep):
    """Require authenticated RCON transport and the exact loaded fixture property."""
    from server import runtime
    from utils.query import QueryError, _source_rcon_command_once

    host = runtime.resolve_query_host(server)
    password = server.data["adminpassword"]
    port = int(server.data["rconport"])
    if command is None:
        command = lambda text, remaining: _source_rcon_command_once(
            host, port, password, min(10, remaining), text)
    if read_logs is None:
        def read_logs():
            root = Path(server.data["dir"]) / "ShooterGame/Saved/Logs"
            native = "\n".join(path.read_text(errors="replace") for path in root.glob("*.log"))
            return native + "\n" + runtime.read_server_logs(server, lines=2000)
    deadline = clock() + timeout
    last = "RCON has not answered"
    while clock() < deadline:
        try:
            last = command("ListPlayers", deadline - clock())
            if last.strip().lower() == "no players connected":
                break
        except QueryError as exc:
            last = str(exc)
        sleep(min(2, max(0, deadline - clock())))
    else:
        raise AssertionError("ARK native RCON never confirmed the empty world: "
                             + last.replace(password, "<redacted>"))
    # Unlike stdin/FIFO delivery, this receives ARK's authenticated command response.
    # GetAll requires a property; SHOWDEFAULTS includes the loaded mod Blueprint CDO.
    response = command(NATIVE_COMMAND, max(0.1, deadline - clock()))
    last = response
    while clock() < deadline:
        try:
            assert_native_object_property(last)
            print("ARK enumerated the loaded Meat Spoiler Blueprint ModName property.")
            return
        except AssertionError:
            last = response + "\n" + read_logs()
            sleep(min(2, max(0, deadline - clock())))
    assert_native_object_property(last.replace(password, "<redacted>"))


def main():
    """Use the configured AlphaGSM runtime host, including Docker sibling gateways."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "check"))
    parser.add_argument("server_name")
    args = parser.parse_args()
    from server import Server

    server = Server(args.server_name)
    if args.action == "prepare":
        prepare_probe(server)
    else:
        probe_native_object(server)


if __name__ == "__main__":
    # Keep the same repository import surface as AlphaGSM's CLI.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    main()
