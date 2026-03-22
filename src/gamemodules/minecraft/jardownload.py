"""Shared helpers for Minecraft-family modules that download a server jar."""

import os

import downloader
from server import ServerError
import utils.updatefs


def install_downloaded_jar(server):
    """Download the configured server artifact and link it into the install dir."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    server_jar = os.path.join(server.data["dir"], server.data["exe_name"])

    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(server_jar)
    ):
        download_name, download_extension = os.path.splitext(server.data["download_name"])
        decompress = ()
        if download_extension == ".zip":
            decompress = ("zip",)
        try:
            downloadpath = downloader.getpath(
                "url", (server.data["url"], download_name + download_extension) + decompress
            )
            if decompress == ():
                try:
                    os.remove(server_jar)
                except FileNotFoundError:
                    pass
                os.symlink(os.path.join(downloadpath, server.data["exe_name"]), server_jar)
            else:
                basetagpath = os.path.join(server.data["dir"], ".~basetag")
                try:
                    oldpath = os.readlink(basetagpath)
                except FileNotFoundError:
                    oldpath = "/dev/null/INVALID"
                else:
                    os.remove(basetagpath)
                utils.updatefs.update(
                    oldpath,
                    downloadpath,
                    server.data["dir"],
                    server.data["download"]["linkdir"],
                    server.data["download"]["copy"],
                )
                os.symlink(downloadpath, basetagpath)
        except downloader.DownloaderError as ex:
            raise ServerError("Error downloading requested server artifact", ex)
        server.data["current_url"] = server.data["url"]
    else:
        print("Skipping download")
    server.data.save()
