"""Team Fortress 2-specific lifecycle, configuration, and update helpers."""

import os
import re

import screen
import server.runtime as runtime_module
from server.settable_keys import SettingSpec
import utils.steamcmd as steamcmd
from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.valve_server import (
    send_console_command_and_collect_response,
    integration_source_server_config,
    source_console_status,
    source_query_address,
    validate_source_startmap,
    wake_source_server_for_a2s,
)

steam_app_id = 232250
steam_anonymous_login_possible = True
STEAMCLIENT_DST = os.path.expanduser("~/.steam/sdk64/steamclient.so")

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
        )
    ),
    "update": CmdSpec(
        options=(
            OptSpec(
                "v",
                ["validate"],
                "Validate the server files after updating",
                "validate",
                None,
                True,
            ),
            OptSpec(
                "r",
                ["restart"],
                "Restarts the server upon updating",
                "restart",
                None,
                True,
            ),
        )
    ),
    "restart": CmdSpec(),
}

# required still
command_descriptions = {
    "update": "Updates the game server to the latest version.",
    "restart": "Restarts the game server without killing the process.",
}

max_stop_wait = 1
config_sync_keys = ("servername", "rconpassword", "serverpassword")
setting_schema = {
    "map": SettingSpec(
        canonical_key="map",
        aliases=("gamemap", "startmap", "level"),
        description="The currently selected map or level.",
        value_type="string",
        apply_to=("datastore", "launch_args"),
        storage_key="startmap",
        examples=("cp_dustbowl",),
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname", "server_name", "name"),
        description="The server's public name shown to players.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("AlphaGSM TF2 Server",),
    ),
    "rconpassword": SettingSpec(
        canonical_key="rconpassword",
        aliases=("rconpass", "rcon_password"),
        description="Remote console password for administrative access.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        aliases=("sv_password", "svpassword", "password"),
        description="Password required for players to join the server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
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

_confpat = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s* (?:\s*(\S+))?(\s*)\Z")
_SOURCE_BOOL_CVAR_RE = re.compile(r'"?(?P<name>[^"=]+)"?\s*=\s*"?(?P<value>[01])"?')


def updateconfig(filename, settings):
    """Rewrite a simple key/value config file with the provided settings."""
    lines = []
    if os.path.isfile(filename):
        settings = settings.copy()
        with open(filename, "r") as f:
            for line in f:
                m = _confpat.match(line)
                if m is not None and m.group(1) in settings:
                    lines.append(m.expand(r"\1 " + settings[m.group(1)] + r"\3"))
                    del settings[m.group(1)]
                else:
                    lines.append(line)
    for k, v in settings.items():
        lines.append(k + " " + v + "\n")
    print(lines)
    with open(filename, "w") as f:
        f.write("".join(lines))


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

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible

    # defaults

    server.data["startmap"] = "cp_dustbowl"
    server.data["maxplayers"] = "16"
    server.data.setdefault("servername", "AlphaGSM TF2 Server")
    server.data.setdefault("rconpassword", "changeme")
    server.data.setdefault("serverpassword", "")

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

    # assign the port to the server
    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        while True:
            inp = input(
                "Please specify the port to use for this server: "
                + ("(current=" + str(port) + ") " if port is not None else "")
            ).strip()
            if port is not None and inp == "":
                break
            try:
                port = int(inp)
            except ValueError:
                print(inp + " isn't a valid port number")
                continue
            break
    if port is None:
        raise ValueError("No Port")
    server.data["port"] = port

    # assign install dir for the server
    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir = server.data["dir"]
        else:
            dir = os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the tf2 server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = os.path.join(
        dir, ""
    )  # guarentees the inclusion of trailing slashes.

    # if exe_name is not asigned, use the function default one
    if "exe_name" not in server.data:
        server.data["exe_name"] = "srcds_run"
    server.data.save()

    return (), {}


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


def doinstall(server):
    """Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater"""
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])

    print("Installing game server at", server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def restart(server):
    """Restart the server by stopping it and then starting it again."""
    server.stop()
    server.start()


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


def update(server, validate=False, restart=False):
    """Update the TF2 install through SteamCMD and optionally restart it."""
    try:
        server.stop()
    except:
        print("Server has probably already stopped, updating")
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


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

    return [
        exe_name,
        "-game",
        "tf",
        "-strictportbind",
        "+ip",
        "0.0.0.0",
        "-port",
        str(server.data["port"]),
        "+clientport",
        str(client_port),
        "+tv_port",
        str(sourcetv_port),
        "+map",
        str(server.data["startmap"]),
        "+servercfgfile",
        "server.cfg",
        "+maxplayers",
        str(server.data["maxplayers"]),
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

    config_values = {
        "hostname": _quote_config_value(
            server.data.get("servername", "AlphaGSM TF2 Server")
        ),
        "rcon_password": _quote_config_value(server.data.get("rconpassword", "changeme")),
        "sv_password": _quote_config_value(server.data.get("serverpassword", "")),
    }
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
    """Report TF2 server status information."""
    pass


def checkvalue(server, key, *value):
    """Validate supported TF2 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] == "maxplayers":
        return str(int(value[0]))
    if key[0] in ("startmap", "map"):
        return validate_source_startmap(server, "tf", value[0])
    if key[0] in ("servername", "hostname", "dir", "exe_name"):
        return str(value[0])
    if key[0] in ("rconpassword", "rcon_password", "serverpassword", "sv_password"):
        return str(value[0])
    raise ServerError("Unsupported key")


## TODO integrate Steam games properly into the downloads module.
##
##
##def doinstall(server):
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
