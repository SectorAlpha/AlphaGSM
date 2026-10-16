"""Verify Workshop VPKs in L4D2's running-engine addon load order."""

import argparse
from pathlib import Path
import re

BEGIN_MARKER = "AlphaGSM-Workshop-Mounts-BEGIN"
END_MARKER = "AlphaGSM-Workshop-Mounts-END"


def assert_workshop_mounts(log_text, item_ids, *, begin_marker=BEGIN_MARKER, end_marker=END_MARKER):
    """Require a completed fresh console probe containing every item's mount."""
    # Echo commands can themselves appear in logs; use complete marker-only lines.
    lines = [line.strip() for line in log_text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == begin_marker]
    assert starts, "No fresh Workshop mount probe began"
    start = starts[-1]
    ends = [index for index in range(start + 1, len(lines)) if lines[index] == end_marker]
    assert ends, "Workshop mount probe did not finish"
    probe = lines[start + 1:ends[0]]
    assert not any('Unknown command' in line for line in probe), "Engine addon load command unavailable"
    mounted = set()
    for line in probe:
        if any(error in line.lower() for error in ("can't", "cannot", "failed", "error", "malformed")):
            continue
        match = re.fullmatch(r'(?:GAME\s+)?"?/[^"\r\n]*/left4dead2/addons/workshop/([0-9]+)\.vpk"?(?:\s+\(vpk\))?',
                             line.replace("\\", "/"))
        if match:
            mounted.add(match.group(1))
    missing = set(map(str, item_ids)) - mounted
    assert not missing, f"Workshop addons not mounted by the running L4D2 server: {sorted(missing)}"


def main():
    """Use the same mount check from the streamed smoke runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path)
    parser.add_argument("item_ids", nargs="+")
    parser.add_argument("--begin-marker", default=BEGIN_MARKER)
    parser.add_argument("--end-marker", default=END_MARKER)
    args = parser.parse_args()
    assert_workshop_mounts(args.log_path.read_text(errors="replace"), args.item_ids,
                           begin_marker=args.begin_marker, end_marker=args.end_marker)
    print(f"L4D2 mounted all {len(args.item_ids)} Workshop VPKs")


if __name__ == "__main__":
    main()
