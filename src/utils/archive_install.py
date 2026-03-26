"""Shared helpers for archive-based dedicated server installers."""

import os
import shutil

import downloader
from server import ServerError


def detect_compression(download_name):
    """Infer the archive compression format from a download filename."""

    name = download_name.lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar.bz2") or name.endswith(".tbz2"):
        return "tar.bz2"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar.gz"
    if name.endswith(".tar.xz") or name.endswith(".txz"):
        return "tar.xz"
    if name.endswith(".tar"):
        return "tar"
    if name.endswith(".7z"):
        return "7z"
    raise ServerError("Unable to determine archive type for '%s'" % download_name)


def sync_tree(source, target):
    """Recursively copy an extracted tree into the install directory."""

    os.makedirs(target, exist_ok=True)
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        target_root = target if rel_root == "." else os.path.join(target, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for dirname in dirs:
            src_dir = os.path.join(root, dirname)
            tgt_dir = os.path.join(target_root, dirname)
            if os.path.islink(src_dir):
                link_target = os.readlink(src_dir)
                if os.path.lexists(tgt_dir):
                    os.remove(tgt_dir)
                os.symlink(link_target, tgt_dir)
                dirs.remove(dirname)
            else:
                os.makedirs(tgt_dir, exist_ok=True)
        for filename in files:
            src_file = os.path.join(root, filename)
            tgt_file = os.path.join(target_root, filename)
            if os.path.islink(src_file):
                link_target = os.readlink(src_file)
                if os.path.lexists(tgt_file):
                    os.remove(tgt_file)
                os.symlink(link_target, tgt_file)
            else:
                shutil.copy2(src_file, tgt_file)


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


def install_binary(server):
    """Download a single binary and place it in the install directory."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(exe_path)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"])
        )
        src = os.path.join(downloadpath, server.data["download_name"])
        shutil.copy2(src, exe_path)
        os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
        server.data["current_url"] = server.data["url"]
    else:
        print("Skipping download")
    server.data.save()
