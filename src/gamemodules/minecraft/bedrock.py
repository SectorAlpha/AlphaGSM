"""Minecraft Bedrock Edition dedicated server helpers."""

import os
import shutil
import urllib.request

import downloader
import screen
from server import ServerError
from utils import backups
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from .custom import updateconfig

import server.runtime as runtime_module

BEDROCK_DOWNLOAD_PAGE = "https://www.minecraft.net/en-us/download/server/bedrock"
BEDROCK_URL_TEMPLATE = (
    "https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-%s.zip"
)
BEDROCK_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Minecraft Bedrock in", str),
        ),
        options=(
            OptSpec(
                "v",
                ["version"],
                "Version of Bedrock to download. Uses the latest visible site version by default.",
                "version",
                "VERSION",
                str,
            ),
            OptSpec(
                "u",
                ["url"],
                "Direct Bedrock server download URL to use instead of the default download page.",
                "url",
                "URL",
                str,
            ),
        ),
    )
}
command_descriptions = {}
command_functions = {}


def _read_download_page():
    """Return the Bedrock download page HTML."""

    request = urllib.request.Request(
        BEDROCK_DOWNLOAD_PAGE, headers={"User-Agent": BEDROCK_USER_AGENT}
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def resolve_bedrock_download(version=None):
    """Resolve the official Bedrock Linux dedicated server zip URL."""

    if version not in (None, "", "latest"):
        return version, BEDROCK_URL_TEMPLATE % (version,)
    page = _read_download_page()
    marker = "https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-"
    start = page.find(marker)
    if start < 0:
        raise ServerError("Unable to locate the latest Bedrock dedicated server download")
    end = page.find(".zip", start)
    if end < 0:
        raise ServerError("Unable to parse the latest Bedrock dedicated server download")
    url = page[start : end + 4]
    version = url.rsplit("bedrock-server-", 1)[1][:-4]
    return version, url


def _resolve_archive_root(downloadpath):
    """Return the extracted archive root directory if there is one."""

    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    if len(directories) == 1:
        return directories[0]
    return downloadpath


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


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="bedrock_server",
    download_name="bedrock-server.zip"
):
    """Collect and store configuration values for a Bedrock server."""

    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {
                "default": {
                    "targets": [
                        "worlds",
                        "server.properties",
                        "permissions.json",
                        "allowlist.json",
                    ]
                }
            },
            "schedule": [("default", 0, "days")],
        }
    server.data.setdefault(
        "backupfiles",
        ["worlds", "server.properties", "permissions.json", "allowlist.json"],
    )

    if url is None:
        version, url = resolve_bedrock_download(version=version)
    server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = download_name
    server.data.setdefault("levelname", server.name)
    server.data.setdefault("gamemode", "survival")
    server.data.setdefault("difficulty", "easy")
    server.data.setdefault("maxplayers", "10")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))

    if port is None:
        port = server.data.get("port", 19132)
    if ask:
        inp = input(
            "Please specify the port to use for this server: [%s] " % (port,)
        ).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Bedrock server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = dir
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Bedrock dedicated server files."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    executable = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(executable)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], "zip")
        )
        _sync_tree(_resolve_archive_root(downloadpath), server.data["dir"])
        server.data["current_url"] = server.data["url"]

    server_properties = os.path.join(server.data["dir"], "server.properties")
    updateconfig(
        server_properties,
        {
            "server-port": str(server.data["port"]),
            "gamemode": str(server.data["gamemode"]),
            "difficulty": str(server.data["difficulty"]),
            "level-name": str(server.data["levelname"]),
            "max-players": str(server.data["maxplayers"]),
            "server-name": str(server.data["servername"]),
        },
    )
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a Bedrock dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return ["env", "LD_LIBRARY_PATH=.", "./" + server.data["exe_name"]], server.data["dir"]


def do_stop(server, j):
    """Stop a running Bedrock server via the console."""

    screen.send_to_server(server.name, "\nstop\n")


def status(server, verbose):
    """Detailed Bedrock status is not implemented yet."""


def message(server, msg):
    """Send a Bedrock chat message through the server console."""

    screen.send_to_server(server.name, "\nsay %s\n" % (msg,))


def backup(server, profile=None):
    """Run the shared backup helper for a Bedrock server."""

    backups.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Bedrock datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backups.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in (
        "exe_name",
        "url",
        "version",
        "dir",
        "levelname",
        "gamemode",
        "difficulty",
        "servername",
    ):
        return str(value[0])
    if key[0] == "maxplayers":
        return str(int(value[0]))
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env=requirements.get("env", {}),
        stdin_open=True,
    )
