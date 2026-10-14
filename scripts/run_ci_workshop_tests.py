#!/usr/bin/env python3
"""Run a CI test command with every anonymous Workshop case required."""

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSHOP_FLAGS = (
    "ALPHAGSM_RUN_WORKSHOP",
    "ALPHAGSM_RUN_ARK_WORKSHOP",
    "ALPHAGSM_RUN_ASRDSERVER_WORKSHOP",
    "ALPHAGSM_RUN_BB2SERVER_WORKSHOP",
    "ALPHAGSM_RUN_DOISERVER_WORKSHOP",
    "ALPHAGSM_RUN_GMOD_WORKSHOP",
    "ALPHAGSM_RUN_INSSERVER_WORKSHOP",
    "ALPHAGSM_RUN_L4D2_WORKSHOP",
    "ALPHAGSM_RUN_NMRIHSERVER_WORKSHOP",
    "ALPHAGSM_RUN_NS2SERVER_WORKSHOP",
    "ALPHAGSM_RUN_SQUAD44_WORKSHOP",
    "ALPHAGSM_RUN_TF2_WORKSHOP",
)
WORKSHOP_TEST_FILES = frozenset(
    f"tests/integration_tests/test_{name}.py" for name in (
        "ark", "asrdserver", "avserver", "bb2server", "btserver", "conanexiles",
        "doiserver", "gmodserver", "insserver", "l4d2server", "nmrihserver",
        "ns2server", "projectzomboid", "seserver", "squadserver", "squad44server",
        "stationeersserver", "terraria_tmodloader", "tf2", "unturned", "wreckfestserver",
    )
)
WORKSHOP_SMOKE_FILES = frozenset(
    path.replace("tests/integration_tests/test_", "tests/smoke_tests/run_").replace(".py", ".sh")
    for path in WORKSHOP_TEST_FILES
)
PYTEST_PLUGIN = "tests.integration_tests.workshop_ci_plugin"


def _required_workshop_smoke(command):
    """Identify the invoked repository smoke without changing unrelated skips."""
    script = command[0]
    if Path(script).name in {"bash", "sh"}:
        if len(command) < 2:
            return False
        script = command[1]
    try:
        relative = Path(script).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    return relative in WORKSHOP_SMOKE_FILES


def main(argv=None):
    """Execute trusted argv, preserving context and rejecting required smoke skips."""
    command = list(sys.argv[1:] if argv is None else argv)
    if not command:
        print("Usage: run_ci_workshop_tests.py COMMAND [ARG ...]", file=sys.stderr)
        return 2
    environment = os.environ.copy()
    environment.update({flag: "1" for flag in WORKSHOP_FLAGS})
    environment["ALPHAGSM_CI_WORKSHOP"] = "1"
    existing_options = environment.get("PYTEST_ADDOPTS", "").strip()
    environment["PYTEST_ADDOPTS"] = " ".join(
        part for part in (existing_options, f"-p {PYTEST_PLUGIN}") if part
    )
    try:
        result = subprocess.run(command, env=environment, check=False)
    except OSError:
        print("Unable to execute CI Workshop command", file=sys.stderr)
        return 127
    if result.returncode == 77 and _required_workshop_smoke(command):
        print("Required anonymous Workshop smoke skipped; prerequisites must be satisfied in CI",
              file=sys.stderr)
        return 1
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
