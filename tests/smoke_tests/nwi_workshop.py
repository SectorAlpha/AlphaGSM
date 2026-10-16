"""Fresh Source filesystem evidence for native Workshop mounts."""

import argparse
from pathlib import Path
import re


def assert_native_mounts(text, app_id, item_ids, token):
    """Accept only completed nonce frames containing actual engine search paths."""
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    lines = [line.strip() for line in text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == f"BEGIN-{token}"]
    assert starts, "No fresh native Workshop filesystem probe began"
    end = next((index for index in range(starts[-1] + 1, len(lines))
                if lines[index] == f"END-{token}"), None)
    assert end is not None, "Native Workshop filesystem probe did not finish"
    frame = "\n".join(lines[starts[-1] + 1:end]).replace("\\", "/")
    mounted = set(re.findall(rf"/workshop/content/{int(app_id)}/([0-9]+)(?=/|\s|$)", frame))
    missing = set(map(str, item_ids)) - mounted
    assert not missing, f"Running engine did not mount Workshop items: {sorted(missing)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path)
    parser.add_argument("app_id", type=int)
    parser.add_argument("token")
    parser.add_argument("item_ids", nargs="+")
    args = parser.parse_args()
    assert_native_mounts(args.log_path.read_text(errors="replace"), args.app_id, args.item_ids, args.token)
    print(f"Engine mounted all {len(args.item_ids)} selected native Workshop items")


if __name__ == "__main__":
    main()
