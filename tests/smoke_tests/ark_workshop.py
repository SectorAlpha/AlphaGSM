"""Require ARK to construct and serve a staged public Workshop map."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


# Author: https://steamcommunity.com/sharedfiles/filedetails/?id=2041231763
# Native map FlatMap; 3.372 MB listed Workshop payload. Linux content is checked
# by the adapter and actual process/Docker compatibility remains a CI assertion.
FIXTURE_ID = "2041231763"
FIXTURE_MAP = "FlatMap"


def configured_fixture_map(server):
    """Select only the declared native map from this exact staged Workshop item."""
    state = server.data.get("mods", {})
    maps = state.get("ark_workshop_maps", {}).get(FIXTURE_ID, {})
    path = maps.get(FIXTURE_MAP, "")
    assert path.startswith(f"/Game/Mods/{FIXTURE_ID}/"), "Fixture map is not staged native Linux content"
    assert path.rsplit("/", 1)[-1] == FIXTURE_MAP, "Workshop descriptor selected the wrong native map"
    return path


def assert_native_world(log_text, launch_map):
    """Require fresh successful engine initialization on the exact custom map URL."""
    prefix = r"^(?:\ufeff)?\[[^\]\r\n]+\]\[\s*\d+\]"
    assert re.search(prefix + r'Server: "[^"\r\n]+" has successfully started!', log_text, re.MULTILINE), (
        "Native ARK world did not complete server initialization")
    assert re.search(prefix + r"Commandline:\s*" + re.escape(launch_map) + r"\?listen(?:\?|\s)",
                     log_text, re.MULTILINE), "Native startup did not execute the exact staged Workshop map"
    assert re.search(prefix + r"Full Startup: [0-9.]+ seconds", log_text, re.MULTILINE), (
        "Native ARK custom-world startup did not finish")


def assert_workshop_map_info(info, expected_port=None):
    """A named desired map, empty startup envelope or TCP fallback is insufficient."""
    assert info.get("protocol") == "a2s" and info.get("map") == FIXTURE_MAP, (
        f"ARK did not serve the native Workshop world {FIXTURE_MAP}: {info!r}")
    maximum = info.get("max_players")
    assert isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0, info
    if expected_port is not None:
        assert info.get("port") == expected_port, info


def wait_for_native_world(server, read_info, timeout=120, *, clock=time.monotonic, sleep=time.sleep):
    """Combine fresh engine startup with real A2S world identity and capacity."""
    launch_map = configured_fixture_map(server)
    logs = Path(server.data["dir"]) / "ShooterGame/Saved/Logs"
    deadline, last, native = clock() + timeout, "", ""
    while clock() < deadline:
        native = "\n".join(path.read_text(errors="replace") for path in logs.glob("*.log"))
        try:
            assert_native_world(native, launch_map)
            assert_workshop_map_info(read_info(), int(server.data["queryport"]))
            print(f"ARK constructed and serves Workshop world {FIXTURE_MAP} item={FIXTURE_ID} path={launch_map}")
            return
        except (AssertionError, ValueError, subprocess.TimeoutExpired) as exc:
            last = str(exc)
            sleep(min(2, max(0, deadline - clock())))
    from server.diagnostics import redact_diagnostic
    detail = redact_diagnostic(server, last + "\n" + native[-16000:])
    raise AssertionError("ARK native Workshop world proof failed: " + detail)


def main():
    """Prepare through AlphaGSM set; check through its exact runtime-aware info API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "check"))
    parser.add_argument("server_name")
    args = parser.parse_args()
    from server import Server

    server = Server(args.server_name)
    if args.action == "prepare":
        server.doset("map", configured_fixture_map(server))
    else:
        script = Path(__file__).resolve().parents[2] / "alphagsm"
        def read_info():
            result = subprocess.run([sys.executable, str(script), args.server_name, "info", "--json"],
                                    check=False, capture_output=True, text=True, timeout=20)
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)
        wait_for_native_world(server, read_info)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    main()
