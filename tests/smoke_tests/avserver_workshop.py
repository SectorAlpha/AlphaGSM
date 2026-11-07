"""Require execution of an anonymously downloaded multiplayer Avorion library."""

import re

FIXTURE_ID = "1722652757"
FIXTURE_NAME = "AzimuthLib"
PROBE = '/run package.path=package.path..";data/scripts/lib/?.lua"; local A=include("azimuthlib-basic"); print("ALPHAGSM_AZIMUTH_RESULT=" .. tostring(A.getInt(42, {0,100})))'


def assert_workshop_loaded(log_text):
    """A staged mod or configured Lua block cannot satisfy the execution check."""
    assert "ALPHAGSM_AZIMUTH_RESULT=42" in log_text, "Native Avorion Lua did not execute AzimuthLib.getInt"
    assert re.search(r"1722652757|AzimuthLib", log_text), "Native mod log did not identify the Workshop library"
    assert 'Error loading mod [1722652757]' not in log_text


def main():
    """Validate captured native console output from a smoke run."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    args = parser.parse_args()
    assert_workshop_loaded(Path(args.log).read_text(errors="replace"))


if __name__ == "__main__":
    main()
