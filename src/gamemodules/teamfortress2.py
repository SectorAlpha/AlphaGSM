"""Team Fortress 2-specific lifecycle, configuration, and update helpers."""

import os
import re

import screen
import server.runtime as runtime_module
from server.settable_keys import build_launch_arg_values, build_native_config_values
import utils.steamcmd as steamcmd
from server import ServerError
from utils.simple_kv_config import rewrite_space_config as updateconfig
from utils.valve_server import (
    send_console_command_and_collect_response,
    integration_source_server_config,
    source_console_status,
    source_query_address,
    VALVE_SERVER_CONFIG_SYNC_KEYS,
    build_valve_server_setting_schema,
    validate_source_startmap,
    wake_source_server_for_a2s,
)
from utils.gamemodules import common as gamemodule_common

steam_app_id = 232250
steam_anonymous_login_possible = True
STEAMCLIENT_DST = os.path.expanduser("~/.steam/sdk64/steamclient.so")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install the server in",
)

# required still
command_descriptions = {
    **gamemodule_common.build_update_restart_command_descriptions(
        "Updates the game server to the latest version.",
        "Restarts the game server without killing the process.",
    ),
}

command_functions = {}

max_stop_wait = 1
config_sync_keys = VALVE_SERVER_CONFIG_SYNC_KEYS
setting_schema = {
    **build_valve_server_setting_schema(
        game_name="TF2 Server",
        default_map="cp_dustbowl",
        max_players=16,
        servername_example="AlphaGSM TF2 Server",
        maxplayers_launch_arg_tokens=("+maxplayers",),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}

_TF2_SERVER_CFG_TEMPLATE = """// Team Fortress 2 server.cfg template
// Place this file at: tf/cfg/server.cfg

// AlphaGSM-managed identity and password settings
hostname "AlphaGSM TF2 Server"
sv_password ""
rcon_password "changeme"

// Gameplay
sv_pure 1
mp_timelimit 30
mp_maxrounds 0
mp_autokick 0

// Logging
log on
sv_logbans 1
sv_logecho 1
sv_logfile 1
"""
_SOURCE_BOOL_CVAR_RE = re.compile(r'"?(?P<name>[^"=]+)"?\s*=\s*"?(?P<value>[01])"?')


def _quote_config_value(value):
    """Return a Source-style quoted config value."""

    text = str(value)
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return text
    return '"' + text.replace('"', '\\"') + '"'


# Team Fortress 2 is probably the most simple example of a steamcmd game
def configure(server, ask, port=None, dir=None, *, exe_name="srcds_run"):
    """
    This function creates the configuration details for the  server

    inputs:
        server: the server object
        ask: whether to request details (e.g port) from the user
        dir: the server installation dir
        *: All arguments after this are keyword only arguments
        exe_name: the executable name of the server
    """

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "cp_dustbowl",
            "maxplayers": "16",
            "servername": "AlphaGSM TF2 Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
    )

    # do we have backup data already? if not initialise the dictionary
    if "backup" not in server.data:
        server.data["backup"] = {}
    if "profiles" not in server.data["backup"]:
        server.data["backup"]["profiles"] = {}
    # if no backup profile exists, create a basic one
    if len(server.data["backup"]["profiles"]) == 0:
        # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
        server.data["backup"]["profiles"]["default"] = {"targets": {}}
    if "schedule" not in server.data["backup"]:
        server.data["backup"]["schedule"] = []
    if len(server.data["backup"]["schedule"]) == 0:
        # if default does not exist, create it
        profile = "default"
        if profile not in server.data["backup"]["profiles"]:
            profile = next(iter(server.data["backup"]["profiles"]))
        # set the default to never back up
        server.data["backup"]["schedule"].append((profile, 0, "days"))

    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the tf2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


doinstall = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
doinstall.__doc__ = "Download or refresh the TF2 server files via SteamCMD."


def install(server):
    """Install or prepare the TF2 server files for this server object."""

    doinstall(server)
    if os.path.isfile(server.data["dir"] + "srcds_run_64"):
        server.data["exe_name"] = "srcds_run_64"
    elif os.path.isfile(server.data["dir"] + "srcds_run"):
        server.data["exe_name"] = "srcds_run"
    sync_server_config(server)
    server.data.save()


# technically this command is not needed since the chosen port is assigned in the runscript, but leaving it commented as an example
#  updateconfig(server_cfg,{"hostport":str(server.data["port"])})


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the server by stopping it and then starting it again."


def prestart(server, *args, **kwargs):
    """Perform TF2-specific setup immediately before the server is started."""
    steamclient_src = os.path.join(steamcmd.STEAMCMD_DIR, "linux64", "steamclient.so")
    steamclient_dir = os.path.dirname(STEAMCLIENT_DST)

    if os.path.isfile(steamclient_src):
        if not os.path.isdir(steamclient_dir):
            os.makedirs(steamclient_dir)
        if os.path.lexists(STEAMCLIENT_DST):
            if (
                os.path.islink(STEAMCLIENT_DST)
                and os.readlink(STEAMCLIENT_DST) == steamclient_src
            ):
                return
            os.remove(STEAMCLIENT_DST)
        os.symlink(steamclient_src, STEAMCLIENT_DST)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the TF2 install through SteamCMD and optionally restart it."


def get_start_command(server):
    """Build the command list used to launch the TF2 dedicated server."""
    # example run ./srcds_run -game tf -port 27015 +maxplayers 32 +map cf_2fort
    exe_name = server.data["exe_name"]
    client_port = min(int(server.data["port"]) + 1, 65535)
    sourcetv_port = min(int(server.data["port"]) + 5, 65535)

    if not os.path.isfile(server.data["dir"] + exe_name):
        for fallback in ("srcds_run_64", "srcds_run"):
            if os.path.isfile(server.data["dir"] + fallback):
                exe_name = fallback
                server.data["exe_name"] = fallback
                server.data.save()
                break
        else:
            raise ServerError("Executable file not found")
    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    return [
        exe_name,
        "-game",
        "tf",
        "-strictportbind",
        "+ip",
        "0.0.0.0",
        *launch_args[:2],
        "+clientport",
        str(client_port),
        "+tv_port",
        str(sourcetv_port),
        *launch_args[2:4],
        "+servercfgfile",
        "server.cfg",
        *launch_args[4:6],
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running TF2 server."""
    screen.send_to_server(server.name, "\nquit\n")


def _parse_bool_cvar(output, cvar_name):
    """Extract a boolean Source cvar value from console output."""

    for line in reversed(output.splitlines()):
        match = _SOURCE_BOOL_CVAR_RE.search(line.strip())
        if match is None:
            continue
        if match.group("name").strip() == cvar_name:
            return match.group("value") == "1"
    return None


def _tf2_hibernation_allowed(server):
    """Return whether TF2 currently allows empty-server hibernation."""

    return send_console_command_and_collect_response(
        server,
        "tf_allow_server_hibernation",
        lambda output: _parse_bool_cvar(output, "tf_allow_server_hibernation"),
        timeout=5.0,
    )


def get_hibernating_console_info(server):
    """Return console-derived info only when TF2 hibernation is enabled."""

    if not _tf2_hibernation_allowed(server):
        return None
    return source_console_status(server)


def get_query_address(server):
    """Return the live TF2 query endpoint."""

    return source_query_address(server)


def get_info_address(server):
    """Return the live TF2 info endpoint."""

    return source_query_address(server)


def sync_server_config(server):
    """Rewrite the TF2 native server.cfg from datastore values."""

    server_cfg_dir = os.path.join(server.data["dir"], "tf", "cfg")
    if not os.path.isdir(server_cfg_dir):
        os.makedirs(server_cfg_dir)

    server_cfg = os.path.join(server_cfg_dir, "server.cfg")
    if not os.path.isfile(server_cfg):
        with open(server_cfg, "w", encoding="utf-8") as handle:
            handle.write(_TF2_SERVER_CFG_TEMPLATE)

    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "servername": "AlphaGSM TF2 Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
        value_transform=lambda _spec, value: _quote_config_value(value),
        require_explicit_key=True,
    )
    integration_cfg = integration_source_server_config()
    if integration_cfg:
        merged_config_values = dict(integration_cfg)
        merged_config_values.update(config_values)
        config_values = merged_config_values
        config_values["tf_allow_server_hibernation"] = "0"
    updateconfig(server_cfg, config_values)


def list_setting_values(server, canonical_key):
    """Return installed map names for the TF2 map setting."""

    if canonical_key != "map":
        return None
    install_dir = server.data.get("dir")
    if not install_dir:
        return []
    maps_dir = os.path.join(install_dir, "tf", "maps")
    if not os.path.isdir(maps_dir):
        return []
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(maps_dir)
        if filename.endswith(".bsp")
    )


def status(server, verbose):
    """Report TF2 server status information using shared query/info helpers.

    If *verbose* is true call `server.info()` for richer output; otherwise
    call `server.query()` for a quick reachability check. Catch and print
    exceptions to remain non-fatal and backward-compatible.
    """
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
    return None


def checkvalue(server, key, *value):
    """Validate supported TF2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_str_keys=("servername", "rconpassword", "serverpassword"),
        raw_int_keys=("port",),
        raw_str_keys=("dir", "exe_name"),
        resolved_handlers={
            "map": lambda server_obj, raw_value: validate_source_startmap(server_obj, "tf", raw_value),
        },
        raw_handlers={
            "maxplayers": lambda _server_obj, raw_value: str(int(raw_value)),
            "startmap": lambda server_obj, raw_value: validate_source_startmap(server_obj, "tf", raw_value),
        },
    )


## TODO integrate Steam games properly into the downloads module.
##
##
## legacy installation sketch:
##  """# Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater """
##  if not os.path.isdir(server.data["dir"]):
##    os.makedirs(server.data["dir"])
##
##  # crashes here.. what is this? AppID:server.data["Steam_AppID"]
##  versions=downloader.getpaths("steamcmd",sort="version",active=True)
##  versions = []
##
##  if len(versions)==0:
##    server.data["version"]=1
##    path=downloader.getpath("steamcmd",(server.data["Steam_AppID"],server.data["dir"],server.data["Steam_anonymous_login_possible"]))
##  else:
##    latest=versions[0]
##    server.data["version"]=latest[1][0]
##    path=latest[2]
##
##  basetagpath=os.path.join(server.data["dir"],".~basetag")
##  try:
##    oldpath=os.readlink(basetagpath)
##  except FileNotFoundError:
##   oldpath="/dev/null/INVALID"
##  if oldpath==path:
##    if update:
##      print("Latest version already downloaded")
##      return
##
##  # for a future release
##  # server.data["version"]+=1;
##
##    path=downloader.getpath("steamcmd",(server.data["Steam_AppID"],server.data["dir"],server.data["Steam_anonymous_login_possible"]))
##    # should now be different as this shouldn't (assuming downloader is working right) return the same path as it did for the old version
##  server.data.save()
##  os.remove(basetagpath)
##  updatefs.update(oldpath,path,server.data["dir"]) #TODO: Fill in the skip, linkdir and copy args
##  os.symlink(downloadpath,basetagpath)


# required, must be defined to allow functions listed below which are not in the defaults to be used
command_functions = {
    "update": update,
    "restart": restart,
}  # will have elements added as the functions are defined

wake_a2s_query = wake_source_server_for_a2s

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
