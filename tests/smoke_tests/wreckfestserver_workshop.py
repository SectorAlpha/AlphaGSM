"""Require native registration of an anonymously downloaded Wreckfest track."""

import argparse
from pathlib import Path
import re

FIXTURE_ID = "3428792631"
FIXTURE_NAME = "Crazy 2025"
TRACK = "crazy_2000_classic"


def assert_workshop_loaded(log_text):
    """A config line or reported mod count cannot satisfy the track registry check."""
    assert re.search(r"(?im)^.*crazy_2000_classic.*$", log_text), "Native track registry did not list the Workshop event"
    assert re.search(r"(?i)tracks", log_text), "The native available-track command did not run"
    assert not re.search(r"(?i)(?:not found|failed to load).*crazy_2000_classic", log_text)


def main():
    """Validate fresh native console output captured by a smoke run."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    assert_workshop_loaded(parser.parse_args().log.read_text(errors="replace"))


if __name__ == "__main__":
    main()
