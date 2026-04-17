"""RimWorld Together dedicated server lifecycle helpers."""

import json
import os

import screen
from server import ServerError
from server.settable_keys import SettingSpec
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
import server.runtime as runtime_module

RIMWORLD_TOGETHER_LATEST_RELEASE_API = (
    "https://api.github.com/repos/RimWorld-Together/Rimworld-Together/releases/latest"
)

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the RimWorld Together server", int),
            ArgSpec("DIR", "The directory to install RimWorld Together in", str),
        ),
        options=(
            OptSpec("v", ["version"], "Version to download.", "version", "VERSION", str),
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("N", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        aliases=("gameport",),
        description="The game port used by the RimWorld Together server.",
        value_type="integer",
        apply_to=("datastore", "native_config", "launch_args"),
        examples=("25555",),
    ),
}


def _update_json_config(path, updates):
    """Merge *updates* into a JSON config file, creating it if needed."""

    settings = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                settings = json.load(fh)
        except (json.JSONDecodeError, OSError):
            settings = {}
    settings.update(updates)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)
        fh.write("\n")


def sync_server_config(server):
    """Keep RimWorld Together config files aligned with the datastore."""

    config_dir = os.path.join(server.data["dir"], "Config")
    os.makedirs(config_dir, exist_ok=True)
    _update_json_config(
        os.path.join(config_dir, "ServerSettings.json"),
        {"Port": server.data["port"]},
    )

    live_config_dir = os.path.join(server.data["dir"], "Configs")
    os.makedirs(live_config_dir, exist_ok=True)
    _update_json_config(
        os.path.join(live_config_dir, "ServerConfig.json"),
        {"Port": server.data["port"]},
    )


def resolve_download(version=None):
    """Resolve the latest RimWorld Together server archive."""

    def _matches(asset):
        name = asset.get("name", "").lower()
        return name.endswith(".zip") and "linux-x64" in name

    from utils.github_releases import resolve_release_asset

    return resolve_release_asset(RIMWORLD_TOGETHER_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="GameServer",
):
    """Collect and store configuration values for a RimWorld Together server."""

    server.data.setdefault("backupfiles", ["Config", "Saves", "Mods"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Config", "Saves", "Mods"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 25555)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the RimWorld Together server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input("Direct archive URL for the RimWorld Together server: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "rimworld-together-server.zip"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the RimWorld Together server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(server.data["url"]))
    install_archive(server, detect_compression(server.data["download_name"]))
    # The GameServer binary ignores the --port command-line argument. Recent
    # builds still generate their live network settings from Configs/
    # ServerConfig.json, so keep both config locations aligned with the port
    # chosen during setup.
    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch a RimWorld Together dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "--port", str(server.data["port"])],
        server.data["dir"],
    )

def get_query_address(server):
    """Return the TCP address used to query the RimWorld Together server.

    RimWorld Together uses a TCP-based protocol on its game port; a TCP
    connect on that port confirms the server is accepting connections.
    """
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def get_info_address(server):
    """Return the TCP address used by the ``info`` command for this server."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def list_setting_values(server, canonical_key):
    """RimWorld Together does not expose enumerated setting values."""

    return None

def do_stop(server, j):
    """Stop RimWorld Together by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed RimWorld Together status is not implemented yet."""


def message(server, msg):
    """RimWorld Together has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a RimWorld Together server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported RimWorld Together datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "version"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
    )
