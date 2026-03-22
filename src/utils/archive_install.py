"""Shared helpers for archive-based dedicated server installers."""

import os
import shutil

import downloader


def sync_tree(source, target):
    """Recursively copy an extracted tree into the install directory."""

    os.makedirs(target, exist_ok=True)
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        target_root = target if rel_root == "." else os.path.join(target, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for dirname in dirs:
            os.makedirs(os.path.join(target_root, dirname), exist_ok=True)
        for filename in files:
            shutil.copy2(os.path.join(root, filename), os.path.join(target_root, filename))


def resolve_archive_root(downloadpath):
    """Return the most likely extracted root directory for an archive download."""

    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    if len(directories) == 1:
        return directories[0]
    return downloadpath


def install_archive(server, compression):
    """Download and install an archive-backed server into the configured dir."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(exe_path)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], compression)
        )
        sync_tree(resolve_archive_root(downloadpath), server.data["dir"])
        server.data["current_url"] = server.data["url"]
    else:
        print("Skipping download")
    server.data.save()
