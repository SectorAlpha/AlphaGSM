"""Team Fortress 2-specific lifecycle, configuration, and update helpers."""

import os
import re

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.fileutils import make_empty_file

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

_confpat = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s* (?:\s*(\S+))?(\s*)\Z")


def _should_force_sv_lan():
    """Return True when TF2 should force LAN mode in integration tests."""
    return os.environ.get("ALPHAGSM_RUN_INTEGRATION") == "1"


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
    if port is None and "port" in server.data:
        port = server.data["port"]
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
    # TODO: any config files that need creating or any commands that need running before the server can start for the first time

    if os.path.isfile(server.data["dir"] + "srcds_run_64"):
        server.data["exe_name"] = "srcds_run_64"
    elif os.path.isfile(server.data["dir"] + "srcds_run"):
        server.data["exe_name"] = "srcds_run"

    # create a default config if the download didn't include one
    server_cfg_dir = server.data["dir"] + "tf/cfg/"
    if not os.path.isdir(server_cfg_dir):
        os.makedirs(server_cfg_dir)

    server_cfg = server_cfg_dir + "server.cfg"
    if not os.path.isfile(server_cfg):
        make_empty_file(server_cfg)
        with open(server_cfg, "w") as f:
            f.write("""// AlphaGSM default TF2 server config
hostname "AlphaGSM TF2 Server"
sv_pure 1
""")
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
    # TODO define a map using the -m optional argument
    exe_name = server.data["exe_name"]
    client_port = min(int(server.data["port"]) + 1, 65535)

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

    steam_updatescript = steamcmd.get_autoupdate_script(
        server.name, server.data["dir"], steam_app_id
    )
    steamcmd_dir = steamcmd.STEAMCMD_DIR

    return [
        exe_name,
        "-game",
        "tf",
        "-port",
        str(server.data["port"]),
        "-clientport",
        str(client_port),
        "+maxplayers",
        str(server.data["maxplayers"]),
        "+sv_pure",
        "1",
        "+ip",
        "0.0.0.0",
        "-secured",
        "-timeout 0",
        "-strictportbind",
        "+randommap",
        "-autoupdate",
        "-steam_dir",
        steamcmd_dir,
        "-steamcmd_script",
        steam_updatescript,
        "+sv_shutdown_timeout_minutes",
        "2",
    ] + (["+sv_lan", "1"] if _should_force_sv_lan() else []), server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running TF2 server."""
    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report TF2 server status information."""
    pass


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
