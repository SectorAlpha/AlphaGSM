"""Common Minecraft server helpers shared by vanilla and related modules."""

import os
import urllib.request
import json
import time
import datetime
import subprocess as sp
from server import ServerError
from server.settable_keys import KeyResolutionError, resolve_requested_key
import re
import screen
import server.runtime as runtime_module
import downloader
import utils.updatefs
from utils.cmdparse.cmdspec import CmdSpec, OptSpec, ArgSpec
from utils import backups
from utils.simple_kv_config import rewrite_equals_config as updateconfig
import random
from .properties_config import (
    CONFIG_SYNC_KEYS,
    build_server_properties_values,
    build_setting_schema,
)


# required tuple
commands = ("op", "deop")

# required
# dictionary command_args
#   key = command name
#   value = CmdSpec(optional argument tuple=(Argument, description, type),
#      options=(Optspec( shortform, longform, description, keyword to store option, default value, store value if true, else run function))
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
        ),
        options=(OptSpec("l", ["eula"], "Mark the eula as read", "eula", None, True),),
    ),
    "op": CmdSpec(
        requiredarguments=(ArgSpec("USER", "The user[s] to op", str),), repeatable=True
    ),
    "deop": CmdSpec(
        requiredarguments=(ArgSpec("USER", "The user[s] to deop", str),),
        repeatable=True,
    ),
    "message": CmdSpec(
        optionalarguments=(
            ArgSpec(
                "TARGET",
                "The user[s] to send the message to. Sends to all if none given.",
                str,
            ),
        ),
        repeatable=True,
        options=(
            OptSpec(
                "p",
                ["parse"],
                "Parse the message for selectors (otherwise prints directly).",
                "parse",
                None,
                True,
            ),
        ),
    ),
    "backup": CmdSpec(
        optionalarguments=(
            ArgSpec("PROFILE", "Do a backup using the specified profile", str),
        ),
        options=(
            OptSpec(
                "a",
                ["activate"],
                "Activate regular backups. Valid values for frequency are 'daily', 'weekly', 'monthly' and 'yearly' or 'none' to disable",
                "activate",
                "FREQUENCY",
                str,
            ),
            OptSpec(
                "d",
                ["deactivate"],
                "Deactivate regular backups. Equivelent to --activate none",
                "activate",
                None,
                "none",
            ),
            OptSpec(
                "w",
                ["when"],
                "When should the regular backups take place. Valid format is 'hour[:minute][ DATE]' where DATE is the day of the week (3 letter names accepted) for "
                "weekly, the day of the month for monthly, the day and month (3 letter names accepted for month) for yearly backups and not allowed for daily backups",
                "when",
                "WHEN",
                str,
            ),
        ),
    ),
}

# required
command_descriptions = {
    "set": "The available keys to set are:\texe_name: (1 value) the name of the jar file to execute\n\tbackup.profiles.PROFILENAME.targets: (many values) the "
    "targets to include in a backup using the specified profile\n\tbackup.profiles.PROFILENAME.exclusions: (many values) patterns that match files to "
    "exclude from a backup using the specified profile\n\tbackup.profiles.PROFILENAME.base: (one value) the name of a profile that this profile extends\n\t"
    "backups.profiles.PROFILENAME.replace_targets and backups.profiles.PROFILENAME.replace_exclusions: (one value: on/off) Should the relevent entry "
    "replace the base rather than extend the bases value\n\tbackups.profiles.PROFILENAME.lifetime: (two values: length year,month,week,day) How long "
    "the backups should be kept for\n\tbackups.schedule.INDEX/APPEND: (3 values: profile timelength timeunit) how long there should be between backups "
    "using that profiles"
}
command_functions = {}  # will have elements added as the functions are defined
config_sync_keys = CONFIG_SYNC_KEYS
setting_schema = build_setting_schema(
    port_description="The port the server listens on.",
    port_example="25565",
    map_example="world",
    maxplayers_example="20",
    servername_description="The server name shown in the client list.",
    servername_example="AlphaGSM Server",
)


def configure(
    server, ask, port=None, dir=None, *, eula=None, exe_name="minecraft_server.jar"
):
    """
    This function creates the configuration details for the minecraft server

    inputs:
        server: the server object
        ask: whether to request details (e.g port) from the user
        dir: the server installation dir
        *: All arguments after this are keyword only arguments
        eula: whether the user agrees to sign the eula
        exe_name: the executable name of the server
    """
    # do we have backup data already? if not initialise the dictionary
    if "backup" not in server.data:
        server.data["backup"] = {}
    if "profiles" not in server.data["backup"]:
        server.data["backup"]["profiles"] = {}
    # if no backup profile exists, create a basic one
    if len(server.data["backup"]["profiles"]) == 0:
        # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
        server.data["backup"]["profiles"]["default"] = {
            "targets": [
                "world",
                "server.properties",
                "whitelist.json",
                "ops.json",
                "banned-ips.json",
                "banned-players.json",
            ]
        }
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
                + (str(port) if port is not None else "")
            ).strip()
            if port is not None and inp == "":
                break
            try:
                port = int(inp)
            except ValueError as v:
                print(inp + " isn't a valid port number")
                continue
            break
    if port is None:
        raise ValueError("No Port")
    server.data["port"] = port
    server.data.setdefault("levelname", server.name)
    server.data.setdefault("gamemode", "survival")
    server.data.setdefault("difficulty", "easy")
    server.data.setdefault("maxplayers", "20")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))

    # assign the installation directory
    if dir is None:
        dir = runtime_module.suggest_install_dir(server, server.data.get("dir"))
        if ask:
            # set a custom location to install the directory?
            inp = input(
                "Where would you like to install the minecraft server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = dir

    # lets sign the eula
    if eula is None:
        if ask:
            eula = input(
                "Please confirm you have read the eula (y/yes or n/no): "
            ).strip().lower() in ("y", "yes")
        else:
            eula = False

    # if exe_name is not asigned, use the function default one
    if not "exe_name" in server.data:
        server.data["exe_name"] = exe_name
    server.data.save()

    # required since we are returning args and kwargs.
    # essentially the default version of this line would be return (),{}
    return (), {"eula": eula}


# install requires the server object. you also feed in the arguments (*) and the kwargs {} from the previous return statement
# as seen at the end of the configure function.
def install(server, *, eula=False):
    """Install or validate the configured custom Minecraft server files."""
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    mcjar = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(mcjar):
        raise ServerError(
            "Can't find server jar ({}). Please place the files in the directory and/or update the 'exe_name' then run setup again".format(
                mcjar
            )
        )
    server.data.save()

    eulafile = os.path.join(server.data["dir"], "eula.txt")
    configfile = os.path.join(server.data["dir"], "server.properties")
    javapath = server.data.get("javapath", "java")
    had_configfile = os.path.isfile(configfile)
    had_eulafile = os.path.isfile(eulafile)
    if eula and not os.path.isfile(eulafile):
        with open(eulafile, "w", encoding="utf-8") as handle:
            handle.write("eula=true\n")
    # Seed server.properties before first boot so new Minecraft releases bind the
    # requested port even when the bundler starts without an existing config.
    sync_server_config(server)
    if not had_configfile or (eula and not had_eulafile):
        print("Starting server to create settings")
        try:
            sp.check_call(
                [javapath, "-jar", server.data["exe_name"], "nogui"],
                cwd=server.data["dir"],
                shell=False,
                timeout=20,
            )
        except sp.CalledProcessError as ex:
            print("Error running server. Java returned status: " + str(ex.returncode))
        except sp.TimeoutExpired:
            print("Error running server. Process didn't complete in time")
    sync_server_config(server)
    if eula:
        updateconfig(eulafile, {"eula": "true"})


def get_start_command(server):
    """Build the command list used to launch a custom Minecraft server."""
    javapath = server.data.get("javapath", "java")
    return [
        javapath,
        "-jar",
        server.data["exe_name"],
        "nogui",
        "--port",
        str(server.data["port"]),
    ], server.data["dir"]


def get_runtime_requirements(server):
    """Return Docker runtime metadata for Java-based Minecraft servers."""

    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    requirements = {
        "engine": "docker",
        "family": "java",
        "java": int(java_major),
        "env": {
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "minecraft_server.jar"),
        },
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "tcp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Java-based Minecraft servers."""

    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "tty": True,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            'exec java -jar "$ALPHAGSM_SERVER_JAR" nogui',
        ],
    }


def do_stop(server, j):
    """Send the console command used to stop a running Minecraft server."""
    runtime_module.send_to_server(server, "\nstop\n")


def status(server, verbose):
    """Report Minecraft server status information."""
    pass


def message(server, msg, *targets, parse=False):
    """Send a chat message or command through the Minecraft server console."""
    if len(targets) < 1:
        targets = ["@a"]
    if parse and "@" in msg:
        msglist = []
        pat = re.compile(r"([^@]*[^\\])?(@.(?:\[[^\]]+\])?)")
        while True:
            match = pat.match(msg)
            if match is None:
                break
            if match.group(1) is not None:
                msglist.append(match.group(1))  # group is optional
                # nothing stopping two selectors straight after each other
            msglist.append({"selector": match.group(2)})
            msg = msg[match.end(0) :]
        msglist.append(msg)
        msgjson = json.dumps(msglist)
    else:
        msgjson = json.dumps({"text": msg})
    cmd = "\n".join("tellraw " + target + " " + msgjson for target in targets)
    print(cmd)
    runtime_module.send_to_server(server, "\n" + cmd + "\n")


def sync_server_config(server):
    """Write supported datastore values to server.properties."""
    server_properties = os.path.join(server.data["dir"], "server.properties")
    updateconfig(
        server_properties,
        build_server_properties_values(
            server,
            servername_key="motd",
            default_port=25565,
            default_levelname=server.name,
            default_maxplayers="20",
            default_servername="AlphaGSM %s" % (server.name,),
        ),
    )


def checkvalue(server, key, *value):
    """Validate a proposed stored setting value for this server type."""
    if key[0] == "TEST":
        return value[0]
    try:
        resolved = resolve_requested_key(key[0], setting_schema)
        key = (resolved.storage_key,) + key[1:]
    except KeyResolutionError:
        pass
    if key == ("port",):
        if len(value) != 1:
            raise ServerError("Only one value supported for 'port'")
        return int(value[0])
    if key == ("exe_name",):
        if len(value) != 1:
            raise ServerError("Only one value supported for 'exe_name'")
        return value[0]
    if key == ("javapath",):
        if len(value) != 1:
            raise ServerError("Only one value supported for 'javapath'")
        return value[0]
    if key == ("maxplayers",):
        if len(value) != 1:
            raise ServerError("Only one value supported for 'maxplayers'")
        return str(int(value[0]))
    if key in (("gamemode",), ("difficulty",), ("levelname",), ("servername",)):
        if len(value) != 1:
            raise ServerError("Only one value supported for '{}'".format(key[0]))
        return str(value[0])
    if key[0] == ("backup"):
        try:
            return backups.checkdatavalue(
                server.data.get("backup", {}), key[1:], *value
            )
        except backups.BackupError as ex:
            raise ServerError(ex)
    raise ServerError("{} invalid key to set".format(".".join(str(k) for k in key)))


def _parsewhen(frequency, when):
    """Parse backup scheduling input into the form expected by backup helpers."""
    if when is None:
        time, rest = None, None
    else:
        time, rest = (when.split(None, 2) + [None, None])[:2]
    if time is None:
        hour, minute = None, None
    else:
        hour, minute = (time.split(":") + [None, None])[
            :2
        ]  # ditch any seconds provided. If no : treat as am hour
    if hour is None:
        hour = random.randint(2, 6)
    if minute is None:
        minute = random.randint(0, 59)
    if frequency == "daily":
        return minute, hour, None, None, None
    elif frequency == "weekly":
        if rest is None:
            rest = random.randint(0, 6)
        return minute, hour, None, None, rest
    elif frequency == "monthly":
        if rest is None:
            rest = random.randint(1, 28)
        return minute, hour, rest, None, None
    else:  # frequency == "yearly"
        if rest is None:
            day, month = None, None
        else:
            day, month = (rest.split("/") + [None, None])[
                :2
            ]  # ditch any year provided. If no / treat as day
        if day is None:
            day = random.randint(1, 28)
        if month is None:
            month = random.randint(1, 12)
        return minute, hour, day, month, None


def backup(server, profile=None, *, activate=None, when=None):
    """Run or schedule a backup using the shared backup subsystem."""
    if activate is None:
        dobackup(server, profile)
    else:
        if profile is not None:
            raise ServerError(
                "Can't specify a profile if activating. Edit the backup schedule to change what backups are done when"
            )
        if activate not in ("weekly", "monthly", "yearly", "daily", "none"):
            raise ServerError(
                "Invalid frequency for backups. Options are 'yearly', 'monthly', 'weekly' or 'daily'"
            )
        import crontab
        from core import program

        programpath = program.PATH
        ct = crontab.CronTab(user=True)
        jobs = (
            (job, job.command.split())
            for job in ct
            if job.is_enabled() and job.command.startswith(programpath)
        )
        jobs = [
            job
            for job, cmd in jobs
            if cmd[0] == programpath and server.name == cmd[1] and cmd[2:] == ["backup"]
        ]
        if activate == "none":
            if len(jobs) == 0:
                raise ServerError("backups aren't active. Can't deactivate")
            else:
                for job in jobs:
                    ct.remove(job)
        else:
            for job in jobs:
                ct.remove(job)
            job = ct.new(command=programpath + " " + server.name + " backup")
            if not job.setall(*_parsewhen(activate, when)):
                print("Error parsing time spec")
                if job.slices[0].parts == []:
                    job.slices[0].parse(random.randint(0, 59))
                if job.slices[1].parts == []:
                    job.slices[1].parse(random.randint(2, 6))
                if activate in ("monthly", "yearly") and job.slices[2].parts == []:
                    job.slices[2].parse(random.randint(1, 28))
                if activate == "yearly" and job.slices[3].parts == []:
                    job.slices[3].parse(random.randint(1, 12))
                if activate == "weekly" and job.slices[4].parts == []:
                    job.slices[4].parse(random.randint(0, 6))
            for slice in job.slices:
                slice.parse(slice.render(True))
            print("Job schedule set to {}".format(job.slices))
        ct.write()


def dobackup(server, profile=None):
    """Execute the actual filesystem backup for a Minecraft server."""
    if runtime_module.check_server_running(server):
        runtime_module.send_to_server(server, "\nsave-off\nsave-all\n")
        time.sleep(30)
    try:
        backups.backup(server.data["dir"], server.data["backup"], profile)
    except backups.BackupError as ex:
        raise ServerError("Error backing up server: {}".format(ex))
    finally:
        if runtime_module.check_server_running(server):
            runtime_module.send_to_server(server, "\nsave-on\nsave-all\n")


def op(server, *users):
    """Grant operator status to one or more Minecraft users."""
    for user in users:
        runtime_module.send_to_server(server, "\nop " + user + "\n")


command_functions["op"] = op


def deop(server, *users):
    """Remove operator status from one or more Minecraft users."""
    for user in users:
        runtime_module.send_to_server(server, "\ndeop " + user + "\n")


command_functions["deop"] = deop


def get_info_address(server):
    """Return the SLP address for the ``info`` command.

    Minecraft uses the Server List Ping (SLP) protocol on its main TCP port,
    which reports player count, max players, server description, and version.
    """
    return (runtime_module.resolve_query_host(server), server.data["port"], "slp")


def get_query_address(server):
    """Return the TCP endpoint used by the ``query`` command."""

    return (runtime_module.resolve_query_host(server), server.data["port"], "tcp")
