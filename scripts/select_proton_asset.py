#!/usr/bin/env python3
"""Select the Proton-GE release archive matching the requested architecture."""

import json
import sys


def main() -> int:
    architecture = sys.argv[1]
    release = json.load(sys.stdin)

    for asset in release.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url") or asset.get("browserDownloadUrl")
        if not name.endswith(".tar.gz"):
            continue
        if not url:
            continue
        if architecture == "x86_64" and "aarch64" not in name.lower():
            print(url)
            return 0
        if architecture == "aarch64" and "aarch64" in name.lower():
            print(url)
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
