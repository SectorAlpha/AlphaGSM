#!/usr/bin/env python3
"""Fetch the immutable Minecraft acceptance fixture and verify its upstream hash."""
import hashlib
from pathlib import Path
import sys
import urllib.request

SHA1 = "64bb6d763bed0a9f1d632ec347938594144943ed"
URL = f"https://piston-data.mojang.com/v1/objects/{SHA1}/server.jar"


def main(destination):
    path = Path(destination)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=120) as response:
            payload = response.read()
        if hashlib.sha1(payload).hexdigest() != SHA1:
            raise ValueError("Minecraft fixture failed upstream checksum verification")
        path.write_bytes(payload)
    if hashlib.sha1(path.read_bytes()).hexdigest() != SHA1:
        raise ValueError("Cached Minecraft fixture failed checksum verification")


if __name__ == "__main__":
    main(sys.argv[1])
