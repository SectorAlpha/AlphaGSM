"""Verify Workshop VPKs mounted by L4D2's running-engine `path` command."""

import argparse
from pathlib import Path
import re

BEGIN_MARKER = "AlphaGSM-Workshop-Mounts-BEGIN"
END_MARKER = "AlphaGSM-Workshop-Mounts-END"


def assert_workshop_mounts(log_text, item_ids):
    """Require a completed fresh console probe containing every item's mount."""
    # Echo commands can themselves appear in logs; use complete marker-only lines.
    lines = [line.strip() for line in log_text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == BEGIN_MARKER]
    assert starts, "No fresh Workshop mount probe began"
    start = starts[-1]
    ends = [index for index in range(start + 1, len(lines)) if lines[index] == END_MARKER]
    assert ends, "Workshop mount probe did not finish"
    probe = lines[start + 1:ends[0]]
    assert not any('Unknown command "path"' in line for line in probe), "Engine path command unavailable"
    mounted = set()
    for line in probe:
        if any(error in line.lower() for error in ("can't", "cannot", "failed", "error", "malformed")):
            continue
        mounted.update(re.findall(r"/left4dead2/addons/workshop/([0-9]+)\.vpk\b", line.replace("\\", "/")))
    missing = set(map(str, item_ids)) - mounted
    assert not missing, f"Workshop addons not mounted by the running L4D2 server: {sorted(missing)}"


def main():
    """Use the same mount check from the streamed smoke runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path)
    parser.add_argument("item_ids", nargs="+")
    args = parser.parse_args()
    assert_workshop_mounts(args.log_path.read_text(errors="replace"), args.item_ids)
    print(f"L4D2 mounted all {len(args.item_ids)} Workshop VPKs")


if __name__ == "__main__":
    main()
