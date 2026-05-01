"""TeamSpeak 3 server lifecycle helpers."""

import os
import pathlib
import re
import shutil
import urllib.request

import downloader
import screen
import server.runtime as runtime_module
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

TEAMSPEAK_DOWNLOADS_PAGE = "https://teamspeak.com/en/downloads"
TEAMSPEAK_URL_TEMPLATE = (
    "https://files.teamspeak-services.com/releases/server/%s/"
    "teamspeak3-server_linux_amd64-%s.tar.bz2"
)
TEAMSPEAK_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"

commands = ()
command_args = gamemodule_common.build_setup_version_url_command_args(
    "The voice port to use for the TeamSpeak 3 server",
    "The directory to install TeamSpeak 3 in",
    url_option=OptSpec(
        "u",
        ["url"],
        "Direct TeamSpeak 3 server download URL to use.",
        "url",
        "URL",
        str,
    ),
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _read_download_page():
    """Return the TeamSpeak downloads page HTML."""

    request = urllib.request.Request(
        TEAMSPEAK_DOWNLOADS_PAGE, headers={"User-Agent": TEAMSPEAK_USER_AGENT}
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def resolve_teamspeak_download(version=None):
    """Resolve the TeamSpeak 3 Linux server tarball URL."""

    if version not in (None, "", "latest"):
        return version, TEAMSPEAK_URL_TEMPLATE % (version, version)
    page = _read_download_page()
    match = re.search(r"releases/server/([0-9]+(?:\.[0-9]+)+)/teamspeak3-server_linux_amd64", page)
    if match is None:
        raise ServerError("Unable to locate the latest TeamSpeak 3 server version")
    version = match.group(1)
    return version, TEAMSPEAK_URL_TEMPLATE % (version, version)


def _sync_tree(source, target):
    """Recursively copy a tree into the install directory."""

    os.makedirs(target, exist_ok=True)
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        target_root = target if rel_root == "." else os.path.join(target, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for dirname in dirs:
            os.makedirs(os.path.join(target_root, dirname), exist_ok=True)
        for filename in files:
            shutil.copy2(os.path.join(root, filename), os.path.join(target_root, filename))


def _resolve_archive_root(downloadpath):
    """Return the extracted archive root directory if there is one."""

    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    if len(directories) == 1:
        return directories[0]
    return downloadpath


def configure(server, ask, port=None, dir=None, *, version=None, url=None, exe_name="ts3server"):
    """Collect and store configuration values for a TeamSpeak 3 server."""

    server.data.setdefault("backupfiles", ["ts3server.sqlitedb", "files", "ts3server.ini"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["ts3server.sqlitedb", "files", "ts3server.ini"]}},
            "schedule": [("default", 0, "days")],
        }

    if url is None:
        version, url = resolve_teamspeak_download(version=version)
    server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = "teamspeak3-server_linux_amd64-%s.tar.bz2" % (version,)
    server.data.setdefault("queryport", "10011")
    server.data.setdefault("filetransferport", "30033")
    server.data.setdefault("license_accepted", True)

    if port is None:
        port = server.data.get("port", 9987)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the TeamSpeak 3 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the TeamSpeak 3 server files."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(exe_path)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], "tar.bz2")
        )
        _sync_tree(_resolve_archive_root(downloadpath), server.data["dir"])
        server.data["current_url"] = server.data["url"]
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a TeamSpeak 3 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "default_voice_port=%s" % (server.data["port"],),
            "query_port=%s" % (server.data["queryport"],),
            "filetransfer_port=%s" % (server.data["filetransferport"],),
            "license_accepted=%s" % (1 if server.data.get("license_accepted", True) else 0,),
        ],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for TeamSpeak 3."""

    requirements = {
        "engine": "docker",
        "family": "service-console",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    ports = []
    if "port" in server.data:
        ports.append(
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        )
    if "queryport" in server.data:
        ports.append(
            {
                "host": int(server.data["queryport"]),
                "container": int(server.data["queryport"]),
                "protocol": "tcp",
            }
        )
    if "filetransferport" in server.data:
        ports.append(
            {
                "host": int(server.data["filetransferport"]),
                "container": int(server.data["filetransferport"]),
                "protocol": "tcp",
            }
        )
    if ports:
        requirements["ports"] = ports
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for TeamSpeak 3."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the TS3 ServerQuery address used to query the TeamSpeak 3 server.

    TeamSpeak 3 exposes a TCP ServerQuery interface on ``queryport``
    (default 10011).  Using the ``"ts3"`` protocol allows AlphaGSM to retrieve
    real server information (name, client count, channel list) via the TS3
    ServerQuery protocol rather than a plain TCP ping.
    """
    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", "10011")), "ts3")


def get_info_address(server):
    """Return the TS3 ServerQuery address used by the ``info`` command."""
    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", "10011")), "ts3")


def do_stop(server, j):
    """Send the standard stop command to TeamSpeak 3."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed TeamSpeak 3 status is not implemented yet."""


def message(server, msg):
    """TeamSpeak 3 has no generic user message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a TeamSpeak 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_credentials(server):
    """Return TS3 ServerQuery admin credentials as (username, password) or None.

    Checks for the ``serverquery_admin_password.txt`` file written by
    TeamSpeak 3 server 3.13.3+ on first run, then falls back to parsing the
    admin password from the AlphaGSM screen log (where TS3 prints it at
    first startup).
    """
    server_dir = pathlib.Path(server.data["dir"])
    # TS3 3.13.3+ writes the admin password to this file on first run.
    pw_file = server_dir / "serverquery_admin_password.txt"
    if pw_file.exists():
        password = pw_file.read_text(errors="replace").strip()
        if password:
            return ("serveradmin", password)

    # Fallback: parse the AlphaGSM screen log for the TS3 admin password line.
    # TS3 prints: loginname= "serveradmin", password= "<pw>" on first startup.
    try:
        log_file = pathlib.Path(screen.logpath(server.name))
        if log_file.exists():
            log_text = log_file.read_text(errors="replace")
            match = re.search(r'loginname= "serveradmin", password= "([^"]+)"', log_text)
            if match:
                return ("serveradmin", match.group(1))
    except Exception:  # noqa: BLE001
        pass

    return None


def checkvalue(server, key, *value):
    """Validate supported TeamSpeak 3 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "filetransferport"):
        return int(value[0])
    if key[0] in ("exe_name", "dir", "url", "version"):
        return str(value[0])
    if key[0] == "license_accepted":
        return str(value[0]).lower() in ("1", "true", "yes", "on")
    raise ServerError("Unsupported key")
