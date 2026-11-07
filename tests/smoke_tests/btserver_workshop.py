"""Evidence contract for a public native multiplayer Barotrauma XML package."""

import re
import argparse
from pathlib import Path

FIXTURE_ID = "2499918466"
FIXTURE_NAME = "BaroCraftables"


def assert_workshop_loaded(log_text):
    """Require an enabled-package hash report and a mod-added engine prefab."""
    assert re.search(r"LocalMods[/\\]alphagsm-2499918466[/\\]Items[/\\]", log_text), (
        "Barotrauma calculatehashes did not enumerate the enabled Workshop package"
    )
    assert re.search(r"- Welding Table(?:\s|\(|$)", log_text), (
        "Native ItemPrefab registry did not contain BaroCraftables' Welding Table"
    )
    assert 'Content package "BaroCraftables" not found' not in log_text


def main():
    """Inspect engine output from a fresh native launch."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path", type=Path)
    assert_workshop_loaded(parser.parse_args().log_path.read_text(encoding="utf-8", errors="replace"))


if __name__ == "__main__":
    main()
