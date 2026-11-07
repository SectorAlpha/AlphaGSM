"""Bounded, read-only SDK revision diagnostics for Squad 44 CI startup failures."""

import configparser
import hashlib
from pathlib import Path
import re


def _file_metadata(path):
    try:
        size = path.stat().st_size
        if size > 128 * 1024 * 1024:
            return {"available": False, "reason": "file exceeds 128 MiB"}
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return {"available": True, "size": size, "sha256": digest.hexdigest()}
    except OSError as error:
        return {"available": False, "reason": type(error).__name__}


def _manifest_metadata(path):
    try:
        with path.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return {"unavailable": "manifest exceeds 1 MiB"}
        text = raw.decode("utf-8", errors="replace")
        result = {}
        build = re.search(r'"buildid"\s*"([0-9]+)"', text)
        sdk = re.search(r'"1006"\s*\{[^{}]*"manifest"\s*"([0-9]+)"', text)
        if build:
            result["buildid"] = build.group(1)
        if sdk:
            result["sdk_depot_manifest"] = sdk.group(1)
        return result
    except OSError as error:
        return {"unavailable": type(error).__name__}


def collect_sdk_metadata(install_dir, steamcmd_dir):
    """Return only hashes, sizes and selected public depot revision fields."""
    install_dir, steamcmd_dir = Path(install_dir), Path(steamcmd_dir)
    return {
        "vendor_sdk": _file_metadata(install_dir / "linux64/steamclient.so"),
        "steam_api": _file_metadata(install_dir / "PostScriptum/Binaries/Linux/libsteam_api.so"),
        "steamcmd_sdk": _file_metadata(steamcmd_dir / "linux64/steamclient.so"),
        "steamcmd_package": _file_metadata(steamcmd_dir / "package/steam_cmd_linux.installed"),
        "server_manifest": _manifest_metadata(install_dir / "steamapps/appmanifest_746200.acf"),
    }


def sdk_metadata_from_config(install_dir, config_path):
    """Find the configured downloader directory without emitting configuration."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_path, encoding="utf-8")
    default = Path.home() / ".local/share/Steam"
    if not default.is_dir():
        default = Path.home() / "Steam"
    directory = parser.get("downloader.steamcmd", "steamcmd_path", fallback=str(default))
    return collect_sdk_metadata(install_dir, Path(directory).expanduser())
