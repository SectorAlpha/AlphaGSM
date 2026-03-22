"""Path of Titans dedicated server lifecycle helpers."""

import os
import stat
import subprocess as sp
import uuid

import downloader
import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

POT_CMD_URL_X64 = "https://launcher-cdn.alderongames.com/AlderonGamesCmd-Linux-x64"
POT_CMD_NAME = "AlderonGamesCmd-Linux"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Path of Titans server", int),
            ArgSpec("DIR", "The directory to install Path of Titans in", str),
        ),
        options=(
            OptSpec("v", ["version"], "Hotfix version to download, defaults to latest.", "version", "VERSION", str),
            OptSpec("a", ["auth-token"], "Alderon auth token for the server host account.", "auth_token", "TOKEN", str),
            OptSpec("b", ["beta-branch"], "Alderon branch key to install.", "beta_branch", "BRANCH", str),
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("N", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _get_updater_path():
    """Download and return the cached AlderonGamesCmd path."""

    download_path = downloader.getpath("url", (POT_CMD_URL_X64, POT_CMD_NAME))
    cmd_path = os.path.join(download_path, POT_CMD_NAME)
    mode = os.stat(cmd_path).st_mode
    os.chmod(cmd_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return cmd_path


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    auth_token=None,
    beta_branch=None,
    url=None,
    download_name=None,
    exe_name="PathOfTitansServer.sh",
):
    """Collect and store configuration values for a Path of Titans server."""

    server.data.setdefault("server_name", "AlphaGSM_%s" % (server.name,))
    server.data.setdefault("server_guid", str(uuid.uuid4()))
    server.data.setdefault("startmap", "Island")
    server.data.setdefault("database", "Local")
    server.data.setdefault("beta_branch", "production")
    server.data.setdefault("maxplayers", "100")
    server.data.setdefault("backupfiles", ["Saved", "Config", "Plugins"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Saved", "Config", "Plugins"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 7777)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Path of Titans server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if version is not None:
        server.data["version"] = str(version)
    if auth_token is not None:
        server.data["auth_token"] = auth_token
    elif "auth_token" not in server.data and ask and url is None:
        inp = input("Alderon auth token for the Path of Titans server host account: ").strip()
        if inp:
            server.data["auth_token"] = inp
    if beta_branch is not None:
        server.data["beta_branch"] = str(beta_branch)
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data and ask:
        inp = input("Direct archive URL for the Path of Titans server override [leave blank for AlderonGamesCmd latest]: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or POT_CMD_NAME
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Install Path of Titans using AlderonGamesCmd or an explicit archive override."""

    if server.data.get("url"):
        install_archive(server, detect_compression(server.data["download_name"]))
        return
    auth_token = server.data.get("auth_token")
    if not auth_token:
        raise ServerError("An Alderon auth token is required for Path of Titans installs")
    cmd_path = _get_updater_path()
    install_cmd = [
        cmd_path,
        "--game",
        "path-of-titans",
        "--server",
        "true",
        "--beta-branch",
        server.data.get("beta_branch", "production"),
        "--auth-token",
        auth_token,
        "--install-dir",
        server.data["dir"],
        "--arch",
        "x86_64",
    ]
    install_cmd.extend(["--hotfix", str(server.data.get("version", "-1"))])
    sp.run(install_cmd, check=True)


def get_start_command(server):
    """Build the command used to launch a Path of Titans dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_target = (
        "%s?listen?MaxPlayers=%s"
        % (server.data.get("startmap", "Island"), server.data["maxplayers"])
    )
    auth_token = server.data.get("auth_token")
    if auth_token:
        return (
            [
                "/usr/bin/env",
                "AG_AUTH_TOKEN=%s" % (auth_token,),
                "./" + server.data["exe_name"],
                launch_target,
                "-nullRHI",
                "-ServerName=%s" % (server.data["server_name"],),
                "-ServerGUID=%s" % (server.data["server_guid"],),
                "-BranchKey=%s" % (server.data.get("beta_branch", "production"),),
                "-Database=%s" % (server.data.get("database", "Local"),),
                "-port=%s" % (server.data["port"],),
                "-log",
            ],
            server.data["dir"],
        )
    return (
        [
            "./" + server.data["exe_name"],
            launch_target,
            "-nullRHI",
            "-ServerName=%s" % (server.data["server_name"],),
            "-ServerGUID=%s" % (server.data["server_guid"],),
            "-BranchKey=%s" % (server.data.get("beta_branch", "production"),),
            "-Database=%s" % (server.data.get("database", "Local"),),
            "-port=%s" % (server.data["port"],),
            "-log",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Path of Titans using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Path of Titans status is not implemented yet."""


def message(server, msg):
    """Path of Titans has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Path of Titans server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Path of Titans datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in (
        "url",
        "download_name",
        "exe_name",
        "dir",
        "server_name",
        "server_guid",
        "startmap",
        "database",
        "beta_branch",
        "auth_token",
        "maxplayers",
        "version",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
