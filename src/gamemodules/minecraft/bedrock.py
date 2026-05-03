"""Minecraft Bedrock Edition dedicated server helpers."""

import os
import re
import shutil
import time
import urllib.error
import urllib.request

import downloader
import screen
from server import ServerError
from utils import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common
from utils.gamemodules.minecraft.properties_config import (
    CONFIG_SYNC_KEYS,
    build_server_properties_values,
    build_setting_schema,
)
from .custom import updateconfig

import server.runtime as runtime_module

BEDROCK_DOWNLOAD_PAGES = (
    "https://www.minecraft.net/en-us/download/server/bedrock",
    "https://www.minecraft.net/en-us/download/server/bedrock/",
)
BEDROCK_URL_TEMPLATE = (
    "https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-%s.zip"
)
BEDROCK_HTTP_HEADERS = {
    # Minecraft.net has been more reliable in CI when the request looks like a normal
    # browser page fetch instead of a custom automation client.
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
BEDROCK_HTTP_RETRIES = 3
BEDROCK_HTTP_RETRY_DELAY_SECONDS = 5
BEDROCK_HTTP_TIMEOUT_SECONDS = 60
BEDROCK_ARCHIVE_DOWNLOAD_TIMEOUT_SECONDS = 900
BEDROCK_FALLBACK_VERSION = "1.26.14.1"
BEDROCK_DOWNLOAD_URL_RE = re.compile(
    r"https://www\.minecraft\.net/bedrockdedicatedserver/bin-linux/"
    r"bedrock-server-([0-9.]+)\.zip"
)

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
config_sync_keys = CONFIG_SYNC_KEYS
setting_schema = build_setting_schema(
    port_description="The port the Bedrock server listens on.",
    port_example="19132",
    map_example="Bedrock level",
    maxplayers_example="10",
    servername_description="The server name shown in Bedrock server listings.",
    servername_example="AlphaGSM Bedrock Server",
)


def _read_download_page():
    """Return the Bedrock download page HTML."""

    last_error = None
    for page_url in BEDROCK_DOWNLOAD_PAGES:
        request = urllib.request.Request(page_url, headers=BEDROCK_HTTP_HEADERS)
        for attempt in range(BEDROCK_HTTP_RETRIES):
            try:
                with urllib.request.urlopen(
                    request, timeout=BEDROCK_HTTP_TIMEOUT_SECONDS
                ) as response:
                    return response.read().decode("utf-8", errors="ignore")
            except (OSError, urllib.error.URLError) as exc:
                last_error = exc
                if attempt + 1 < BEDROCK_HTTP_RETRIES:
                    time.sleep(BEDROCK_HTTP_RETRY_DELAY_SECONDS)
    raise ServerError(
        "Unable to fetch the Bedrock dedicated server download page"
    ) from last_error


def resolve_bedrock_download(version=None):
    """Resolve the official Bedrock Linux dedicated server zip URL."""

    if version not in (None, "", "latest"):
        return version, BEDROCK_URL_TEMPLATE % (version,)
    page = _read_download_page()
    match = BEDROCK_DOWNLOAD_URL_RE.search(page)
    if match is None:
        # Minecraft.net now embeds Bedrock download choices behind frontend config ids
        # in the raw HTML. Keep setup working by falling back to the last verified
        # official Linux version until Mojang exposes a stable non-JS resolver again.
        return BEDROCK_FALLBACK_VERSION, BEDROCK_URL_TEMPLATE % (BEDROCK_FALLBACK_VERSION,)
    version = match.group(1)
    url = match.group(0)
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
        dir = runtime_module.suggest_install_dir(server, server.data.get("dir"))
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


def sync_server_config(server):
    """Write supported datastore values to server.properties."""

    server_properties = os.path.join(server.data["dir"], "server.properties")
    updateconfig(
        server_properties,
        build_server_properties_values(
            server,
            setting_schema=setting_schema,
            servername_key="server-name",
            default_port=19132,
            default_levelname=server.name,
            default_maxplayers="10",
            default_servername="AlphaGSM %s" % (server.name,),
            use_defaults=False,
        ),
    )


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
            "url",
            (
                server.data["url"],
                server.data["download_name"],
                "zip",
                str(BEDROCK_ARCHIVE_DOWNLOAD_TIMEOUT_SECONDS),
                "curl",
            ),
        )
        _sync_tree(_resolve_archive_root(downloadpath), server.data["dir"])
        os.chmod(executable, os.stat(executable).st_mode | 0o111)
        server.data["current_url"] = server.data["url"]

    sync_server_config(server)
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
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Bedrock status is not implemented yet."


message = gamemodule_common.make_server_message_hook(
    command="say",
    runtime_module=runtime_module,
)
message.__doc__ = "Send a Bedrock chat message through the server console."


def backup(server, profile=None):
    """Run the shared backup helper for a Bedrock server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Bedrock datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("map", "gamemode", "difficulty", "servername"),
        resolved_handlers={"maxplayers": lambda _server, *values: str(int(values[0]))},
        raw_str_keys=("exe_name", "url", "version", "dir", "levelname"),
        backup_module=backup_utils,
    )


def get_query_address(server):
    """Return the TCP endpoint used by the ``query`` command."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def get_info_address(server):
    """Return the SLP address used by the ``info`` command."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "slp")

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
        tty=True,
    )
