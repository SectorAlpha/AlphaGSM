"""Require native Workshop installation and execution of the public MP fixture."""

import argparse
from pathlib import Path
import re

FIXTURE_ID = "2773478544"
FIXTURE_MOD_ID = "PrintIngameTimeOneHour"


def assert_workshop_loaded(log_text):
    """A configured INI or staged download alone cannot satisfy this check."""
    assert re.search(r"Workshop:.*(?:-> Ready ID=2773478544|2773478544 installed to)", log_text), (
        "Native Project Zomboid engine did not install/ready the Workshop fixture"
    )
    assert "loading PrintIngameTimeOneHour" in log_text, "Native engine did not activate the fixture Mod ID"
    assert re.search(r"Date in game \(dd/mm/yyyy\) - \d{2}/\d{2}/\d{4}", log_text), (
        "PrintIngameTimeOneHour server Lua did not execute on this fresh launch"
    )
    assert not re.search(r'required mod ["\'](?:\\)?PrintIngameTimeOneHour["\'] not found', log_text), (
        "Native Project Zomboid mod loader could not resolve the fixture Mod ID"
    )


def main():
    """Check a fresh native server-console log from process or Docker."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path", type=Path)
    arguments = parser.parse_args()
    assert_workshop_loaded(arguments.log_path.read_text(encoding="utf-8", errors="replace"))


if __name__ == "__main__":
    main()
