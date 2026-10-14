"""Require execution of the selected MES Workshop server framework."""

import argparse
from pathlib import Path
import re

FIXTURE_ID = "1521905890"


def assert_workshop_executed(text):
    """Require the mod's own LoadData logger and a ready game in a fresh log.

    MES_SessionCore.LoadData calls SpawnLogger.Setup, which emits this forced
    native game-log message. A Workshop ID/name in download or config output
    cannot establish that the engine actually compiled and executed the mod.
    """
    assert "Game ready" in text, "Space Engineers did not finish native world startup"
    assert re.search(r"MES Spawner / Startup: Active Debug (?:Not Found|Loaded:)", text), (
        "Engine did not execute the Modular Encounters Systems session script")
    assert "MOD_CRITICAL_ERROR" not in text, "Engine reported a critical mod execution error"


def main():
    """Validate native logs from the smoke runner's fresh disposable install."""
    parser = argparse.ArgumentParser()
    parser.add_argument("install", type=Path)
    args = parser.parse_args()
    logs = list(args.install.glob("SpaceEngineersDedicated_*.log"))
    assert logs, "Space Engineers did not create a fresh native log"
    assert_workshop_executed(max(logs, key=lambda path: path.stat().st_mtime).read_text(errors="replace"))


if __name__ == "__main__":
    main()
