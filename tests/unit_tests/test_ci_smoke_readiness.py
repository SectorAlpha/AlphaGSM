"""Replay smoke lifecycle decisions using successful CI log messages."""

import os
import subprocess

import pytest

from tests.helpers import REPO_ROOT


GOLDSRC = ("bdserver", "csserver", "csczserver", "dmcserver", "dodserver",
           "hldmserver", "opforserver", "ricochetserver", "svenserver", "tfcserver")
SOURCE = ("bb2server", "bmdmserver", "ccserver", "counterstrike2", "cssserver",
          "dodsserver", "doiserver", "emserver", "fofserver", "gmodserver",
          "hl2dmserver", "hldmsserver", "insserver", "l4dserver", "l4d2server",
          "nmrihserver", "pvkiiserver", "tf2")


@pytest.mark.parametrize("module", GOLDSRC + SOURCE + (
    "argoserver", "lifeisfeudalserver", "groundbranchserver", "solserver", "pcarserver",
    "notdserver", "noonesurvivedserver", "icarusserver", "soulmask", "codwawserver",
    "arksurvivalascended", "onsetserver", "exfilserver",
    ))
@pytest.mark.parametrize("query_rc", [0, 1])
def test_smoke_readiness_requires_protocol_response(tmp_path, module, query_rc):
    script = (REPO_ROOT / f"tests/smoke_tests/run_{module}.sh").read_text()
    start = (
        'run_start_with_port_retry "$SERVER_NAME"'
        if module == "arksurvivalascended"
        else 'run_alphagsm "$SERVER_NAME" start'
    )
    lifecycle = script[script.index(start):]
    log = tmp_path / "server.log"
    log.write_text(
        "Connection to Steam servers successful.\n"
        "VAC secure mode is activated.\n"
        "Server loaded. Entering simulation...\n"
        "GameNetDriver SteamSocketsNetDriver_1 started listening on 27015\n"
        "LogNet: IpNetDriver listening on port 27015\n"
    )
    commands = tmp_path / "commands"
    prelude = '''set -Eeuo pipefail
SERVER_NAME=test
START_TIMEOUT_SECONDS=1
run_alphagsm() { echo "$*" >> "$COMMANDS"; }
run_start_with_port_retry() { echo "$1 start" >> "$COMMANDS"; }
wait_for_ready() { grep -Eq "${3:-ready|started|listening|Done}" "$1"; }
wait_for_log_ready() { wait_for_ready "$@"; }
wait_for_info_protocol() { echo "protocol $2" >> "$COMMANDS"; return "$QUERY_RC"; }
run_stop_or_skip() { echo stop >> "$COMMANDS"; }
'''
    result = subprocess.run(["bash", "-c", prelude + lifecycle], capture_output=True,
                            env=dict(os.environ, LOG_PATH=str(log), COMMANDS=str(commands),
                                     QUERY_RC=str(query_rc), PORT="27015"), check=False)
    calls = commands.read_text().splitlines()
    assert (result.returncode == 0) == (query_rc == 0)
    protocol = {
        "solserver": "soldat",
        "soulmask": "tcp",
        "icarusserver": "tcp",
        "notdserver": "tcp",
        "noonesurvivedserver": "tcp",
        "codwawserver": "quake",
        "arksurvivalascended": "source_rcon",
        "onsetserver": "tcp",
        "groundbranchserver": "udp",
        "exfilserver": "udp",
    }.get(module, "a2s")
    protocol_call = f"protocol {protocol}"
    assert protocol_call in calls
    if query_rc == 0:
        assert calls.index(protocol_call) < calls.index("test query") < calls.index("stop")
        assert "test info --json" in calls


def test_palworld_accepts_its_listening_message(tmp_path):
    script = (REPO_ROOT / "tests/smoke_tests/run_palworld.sh").read_text()
    readiness = next(line for line in script.splitlines() if line.startswith("wait_for_ready "))
    log = tmp_path / "server.log"
    log.write_text("Running Palworld dedicated server on :28116\n")
    result = subprocess.run(["bash", "-c", '''
START_TIMEOUT_SECONDS=1
wait_for_ready() { grep -Eq "${3:-ready|started|listening|Done}" "$1"; }
''' + readiness], capture_output=True, env=dict(os.environ, LOG_PATH=str(log)), check=False)
    assert result.returncode == 0
