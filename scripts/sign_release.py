#!/usr/bin/env python3
"""Prepare platform signing, sign releases and discard temporary credentials.

Only trusted tag builds invoke this script. Missing signing/notarization
credentials fail the release before publication; ordinary PR artifacts remain
unsigned. Commands use argument lists and never echo credentials.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import zipfile


def required(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError("Release signing requires " + name)
    return value


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        # Provider output may echo command-line credentials.
        raise RuntimeError("Release signing command failed: " + str(args[0]))
    return result.stdout


def export(name, value):
    if "\n" in value or "\r" in value:
        raise ValueError("Signing values must be single-line")
    with open(required("GITHUB_ENV"), "a", encoding="utf-8") as handle:
        handle.write(name + "=" + value + "\n")


def prepare(root):
    root.mkdir(mode=0o700, exist_ok=True)
    certificate = root / "identity.pfx"
    certificate.write_bytes(base64.b64decode(required("ALPHAGSM_SIGN_PFX"), validate=True))
    certificate.chmod(0o600)
    password = required("ALPHAGSM_SIGN_PASSWORD")
    if sys.platform == "darwin":
        identity = required("ALPHAGSM_CODESIGN_IDENTITY")
        keychain = root / "signing.keychain-db"
        key = secrets.token_hex(32)
        run("security", "create-keychain", "-p", key, str(keychain))
        run("security", "set-keychain-settings", "-lut", "3600", str(keychain))
        run("security", "unlock-keychain", "-p", key, str(keychain))
        run("security", "import", str(certificate), "-k", str(keychain), "-P", password,
            "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
        run("security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:",
            "-s", "-k", key, str(keychain))
        run("security", "list-keychains", "-d", "user", "-s", str(keychain))
        export("ALPHAGSM_CODESIGN_IDENTITY", identity)


def sign(root):
    suffix = ".exe" if os.name == "nt" else ""
    binary = Path("release-artifacts") / (required("ARTIFACT_NAME") + suffix)
    if os.name == "nt":
        kits = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Windows Kits/10/bin"
        candidates = sorted(kits.glob("*/x64/signtool.exe"))
        if not candidates:
            raise RuntimeError("Windows SDK signtool is required")
        tool = str(candidates[-1])
        run(tool, "sign", "/f", str(root / "identity.pfx"), "/p", required("ALPHAGSM_SIGN_PASSWORD"),
            "/fd", "SHA256", "/tr", "http://timestamp.digicert.com", "/td", "SHA256", str(binary))
        run(tool, "verify", "/pa", str(binary))
    elif sys.platform == "darwin":
        # PyInstaller signs nested binaries using the prepared identity.
        run("codesign", "--verify", "--deep", "--strict", str(binary))
        archive = root / "notarize.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            handle.write(binary, binary.name)
        result = json.loads(run("xcrun", "notarytool", "submit", str(archive),
                                "--apple-id", required("ALPHAGSM_APPLE_ID"),
                                "--team-id", required("ALPHAGSM_APPLE_TEAM_ID"),
                                "--password", required("ALPHAGSM_APPLE_PASSWORD"),
                                "--wait", "--timeout", "15m", "--output-format", "json"))
        if result.get("status") != "Accepted":
            raise RuntimeError("Apple notarization did not accept the executable")
    else:
        raise ValueError("Platform signing is only configured for Windows and macOS")
    # Signing changes bytes, so replace the original unsigned checksum.
    binary.with_name(binary.name + ".sha256").write_text(
        hashlib.sha256(binary.read_bytes()).hexdigest() + "  " + binary.name + "\n", encoding="utf-8")


def cleanup(root):
    import shutil
    keychain = root / "signing.keychain-db"
    if sys.platform == "darwin" and keychain.exists():
        run("security", "delete-keychain", str(keychain))
    shutil.rmtree(root, ignore_errors=True)


def main():
    root = Path(required("RUNNER_TEMP")) / "alphagsm-signing"
    {"prepare": prepare, "sign": sign, "cleanup": cleanup}[sys.argv[1]](root)


if __name__ == "__main__":
    main()
