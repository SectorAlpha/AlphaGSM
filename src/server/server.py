"""The core server class and the related ServerError exception

We also define in here the constants that specify the path where server data stores are saved
(DATAPATH) and what package game server modules are searched for in (SERVERMODULEPACKAGE).

For details of how to write a game server module see the gamemodules module in this package.
"""

import json
import os
import subprocess as sp
from . import data
from importlib import import_module
import screen
import time
import crontab
from utils.cmdparse.cmdspec import CmdSpec, ArgSpec, OptSpec
from utils.settings import settings
from collections.abc import Mapping as MappingABC

__all__ = ["Server", "ServerError"]

DATAPATH = os.path.expanduser(
    settings.user.getsection("server").get(
        "datapath",
        os.path.join(
            settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm"), "conf"
        ),
    )
)
SERVERMODULEPACKAGE = settings.system.getsection("server").get(
    "servermodulespackage", "gamemodules."
)


class ServerError(Exception):
    """An Exception thrown when there is an error with the server"""

    pass


_DISABLED_SERVERS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "disabled_servers.conf",
)


def _load_disabled_servers():
    """Load the disabled servers list from disabled_servers.conf.

    Returns a dict mapping module name to reason string.
    """
    disabled = {}
    if not os.path.isfile(_DISABLED_SERVERS_PATH):
        return disabled
    with open(_DISABLED_SERVERS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            module_name = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else "No reason given"
            disabled[module_name] = reason
    return disabled


def _findmodule(name):
    """Resolve a game module name, following namespace and alias indirection."""
    disabled = _load_disabled_servers()
    while True:
        name = str(name)
        if name in disabled:
            raise ServerError(
                "Server module '" + name + "' is currently disabled: "
                + disabled[name]
                + "\nIf you'd like to help fix this, please open an issue or "
                "submit a pull request."
            )
        if len(name) < 2 and all(
            (len(el) > 0 and el.isalnum()) for el in name.split(".")
        ):
            raise ServerError("Invalid module requested: " + self.data["module"])
        try:
            module = import_module(SERVERMODULEPACKAGE + name)
        except ImportError as ex:
            raise ServerError("Can't find module: " + name, ex)
        if not hasattr(
            module, "__file__"
        ):  # no filesystem path so must be a namespace path
            name = name + ".DEFAULT"
            continue
        try:
            name = module.ALIAS_TARGET
        except AttributeError:
            return name, module


class Server(object):
    """An object that represents a game server

    Each instance of this class corresponds to a specific game server with a specified backend.


    Class Attributes: (DO NOT CHANGE)
        default_commands: the default list of commands that all servers handle.
        default_command_args: the default arguments for each of the commands specified in this package.
                    More arguments can be specified by the backend module but these are required to be optional.
        default_command_description: the default description for each of the commands specified in this package.
                    Extra description can be provided by the backend module which is appended to this description.

    Instance Attributes:
        self.name: the name of this server. DO NOT CHANGE
        self.module: the module object for the backend of this server. DO NOT CHANGE
        self.data: the backend data store for this server. DO NOT REPLACE
    """

    default_commands = (
        "setup",
        "start",
        "stop",
        "restart",
        "kill",
        "activate",
        "deactivate",
        "status",
        "send",
        "message",
        "connect",
        "logs",
        "dump",
        "set",
        "backup",
        "restore",
        "wipe",
        "query",
        "info",
    )
    default_command_args = {
        "setup": CmdSpec(
            options=(
                OptSpec(
                    "n",
                    ["noask"],
                    "Don't ask for input. Just fail if we can't cope",
                    "ask",
                    None,
                    False,
                ),
            )
        ),
        "start": CmdSpec(),
        "stop": CmdSpec(),
        "activate": CmdSpec(
            options=(
                OptSpec(
                    "d",
                    ["delay"],
                    "Delay starting the server just setup the crontab",
                    "start",
                    None,
                    False,
                ),
            )
        ),
        "deactivate": CmdSpec(
            options=(
                OptSpec(
                    "d",
                    ["delay"],
                    "Delay stopping the server just remove the crontab",
                    "stop",
                    None,
                    False,
                ),
            )
        ),
        "status": CmdSpec(
            options=(
                OptSpec(
                    "v",
                    ["verbose"],
                    "Verbose status. argument is the level from 0 (normal) to 3 (max)",
                    "verbose",
                    "LEVEL",
                    int,
                ),
            )
        ),
        "restart": CmdSpec(),
        "kill": CmdSpec(),
        "send": CmdSpec(
            requiredarguments=(
                ArgSpec("INPUT", "The text to send to the server console", str),
            )
        ),
        "message": CmdSpec(
            requiredarguments=(ArgSpec("MESSAGE", "The message to send", str),)
        ),
        "connect": CmdSpec(),
        "logs": CmdSpec(
            options=(
                OptSpec(
                    "n",
                    ["lines"],
                    "Number of lines to show (default 50)",
                    "lines",
                    "N",
                    int,
                ),
            )
        ),
        "dump": CmdSpec(),
        "set": CmdSpec(
            requiredarguments=(
                ArgSpec(
                    "KEY", "The key to set in the form of dot seperated elements", str
                ),
            ),
            optionalarguments=(
                ArgSpec(
                    "VALUE",
                    "The value to set. New nodes in the structure will be created as needed. "
                    "Exactly how many values can be specified is KEY dependant.",
                    str,
                ),
            ),
            repeatable=True,
        ),
        "backup": CmdSpec(),
        "restore": CmdSpec(
            optionalarguments=(
                ArgSpec(
                    "BACKUP",
                    "Backup file name or index to restore. "
                    "If omitted, available backups are listed.",
                    str,
                ),
            )
        ),
        "wipe": CmdSpec(),
        "query": CmdSpec(),
        "info": CmdSpec(
            options=(
                OptSpec(
                    "j",
                    ["json"],
                    "Output result as JSON instead of human-readable text",
                    "as_json",
                    None,
                    True,
                ),
                OptSpec(
                    "d",
                    ["detailed"],
                    "Include extended details (e.g. TeamSpeak 3 channel list)",
                    "detailed",
                    None,
                    True,
                ),
            )
        ),
    }
    default_command_descriptions = {
        "setup": "Setup the game server.\nThis will include processing the required settings,"
        " downloading or copying any needed files and doing any setup task so that a"
        " 'start' should work.\nIf noask is specified then this may fail if extra "
        "game server dependant settings are not provided.",
        "start": "Start the server.",
        "stop": "Stop the server.",
        "restart": "Stop the server and start it again.",
        "kill": "Force-kill the server process immediately without a graceful shutdown.",
        "activate": "Set the server to restart on reboots and start now unless --delay is specified.",
        "deactivate": "Stop the server from restarting on reboots and stop now unless --delay is specified.",
        "status": "Check the status of the server. At the minimum will report if the server is running.",
        "send": "Send a line of text directly to the server console (for admin commands, not player chat).",
        "message": "Message the server. By default sends the message to all users.",
        "connect": "Connect to the server's console session.",
        "logs": "Show the last lines of the server console log (default 50). Use -n to change the count.",
        "dump": "Dump the servers data store.",
        "set": "Set a parameter in data store to a new value.\nFor keys that index into lists the special entry 'APPEND' my be used to create a new "
        "entry at the end of the list. Also for some keys value 'DELETE' is a value that causes the entry to be deleted.\n\n"
        "Which values are changable is game module dependent",
        "backup": "Backup the game server",
        "restore": "Restore the game server from a backup.\n"
        "With no argument, lists available backups with their index numbers.\n"
        "Pass an index or the exact filename to restore that backup.\n"
        "The server will be stopped first if it is running.",
        "wipe": "Delete game-world data for supported server types.\n"
        "The server must be stopped before wiping. "
        "Which files are removed is defined by the game module.",
        "query": "Query the game server to check whether it is responding.\n"
        "Uses the Source A2S protocol when a query port is configured, "
        "otherwise falls back to a TCP ping on the game port.",
        "info": "Retrieve detailed server information: player count, map, version, etc.\n"
        "For Minecraft servers uses the Server List Ping (SLP) protocol.\n"
        "For Source/Steam servers uses A2S_INFO.  Falls back to a TCP ping.\n"
        "Use -j / --json to emit the result as a JSON object.\n"
        "Use -d / --detailed to include extended data (e.g. TeamSpeak 3 channel list).",
    }

    def __init__(self, name, module=None):
        """Initialise this Server object.

        If module is not None this is a new Server so initialise it with a data store containing
        only the module name otherwise load the data from the data store and use the module specified there.

        Raises a ServerError if we can't load the data store or if the module isn't specified or can't be loaded.
        """
        self.name = name
        if module is not None:
            if not os.path.isdir(DATAPATH):
                try:
                    os.makedirs(DATAPATH)
                except OSError:
                    raise ServerError(
                        "Data Path doesn't exist and can't create it", DATAPATH
                    )
            self.data = data.JSONDataStore(
                os.path.join(DATAPATH, name + ".json"), {"module": module}
            )
            try:
                self.data.save()
            except IOError as ex:
                raise ServerError("Error saving initial data", ex)
        else:
            try:
                self.data = data.JSONDataStore(os.path.join(DATAPATH, name + ".json"))
            except (IOError, data.DataError) as ex:
                raise ServerError("Error reading data", ex)
        if "module" not in self.data:
            raise ServerError("Invalid data store: No module specified")
        truename, self.module = _findmodule(self.data["module"])
        if truename != self.data["module"]:
            print(
                "Module has been redirected. Actual module is '"
                + truename
                + "'. Saving to data store."
            )
            self.data["module"] = truename
            self.data.save()

    def get_commands(self):
        """Get a list of all the commands available for this server"""
        return self.default_commands + self.module.commands

    def get_command_args(self, command):
        """Get the full argument spec for the command specified on this server"""
        args = self.default_command_args.get(command, None)
        extra_args = self.module.command_args.get(command, None)
        if args is None:
            return extra_args
        return args.combine(extra_args)

    def get_command_description(self, command):
        """Get the complete description for the command specified for this server"""
        desc = self.default_command_descriptions.get(command, None)
        extra_desc = self.module.command_descriptions.get(command, None)
        if extra_desc is not None:
            if desc is None:
                desc = extra_desc
            else:
                desc = desc + "\n\n" + extra_desc
        return desc

    def run_command(self, command, *args, **kwargs):
        """Run the specified command with the specified arguments on this server

        This raises ServerError if the command can't be found or the server state isnt valid
        for the requested command (e.g. stop command on a server that isn't running).

        It can also raise AttributeError if the backend modules doesn't provide some of the
        required functions. It can also raise other Exceptions if the arguments don't match those
        required by either this or the backend module
        """
        if command in self.default_commands:
            if command == "setup":
                self.setup(*args, **kwargs)
            elif command == "start":
                self.start(*args, **kwargs)
            elif command == "stop":
                self.stop(*args, **kwargs)
            elif command == "restart":
                self.restart(*args, **kwargs)
            elif command == "kill":
                self.kill(*args, **kwargs)
            elif command == "activate":
                self.activate(*args, **kwargs)
            elif command == "deactivate":
                self.deactivate(*args, **kwargs)
            elif command == "status":
                self.status(*args, **kwargs)
            elif command == "send":
                self.send(*args, **kwargs)
            elif command == "message":
                self.module.message(self, *args, **kwargs)
            elif command == "connect":
                self.connect(*args, **kwargs)
            elif command == "logs":
                self.logs(*args, **kwargs)
            elif command == "dump":
                self.dump(*args, **kwargs)
            elif command == "set":
                self.doset(*args, **kwargs)
            elif command == "backup":
                self.module.backup(self, *args, **kwargs)
            elif command == "restore":
                self.restore(*args, **kwargs)
            elif command == "wipe":
                self.wipe(*args, **kwargs)
            elif command == "query":
                self.query(*args, **kwargs)
            elif command == "info":
                self.info(*args, **kwargs)
        elif command in self.module.commands:
            self.module.command_functions[command](self, *args, **kwargs)
        else:
            raise ServerError(
                "Unknown command '"
                + command
                + "' can't be executed. Please check the help"
            )

    def setup(self, *args, ask=True, **kwargs):
        """Setup this server. Once this returns the server should be ready to start."""
        args, kwargs = self.module.configure(self, ask, *args, **kwargs)
        self.module.install(self, *args, **kwargs)

    def start(self, *args, **kwargs):
        """Start a server. Won't start it if the server is already running."""
        if screen.check_screen_exists(self.name):
            raise ServerError("Error: Can't start server that is already running")
        try:
            prestart = self.module.prestart
        except AttributeError:
            pass
        else:
            prestart(self, *args, **kwargs)
        cmd, cwd = self.module.get_start_command(self, *args, **kwargs)
        screen.start_screen(self.name, cmd, cwd=cwd)
        try:
            poststart = self.module.poststart
        except AttributeError:
            pass
        else:
            poststart(self, *args, **kwargs)

    def stop(self, *args, **kwargs):
        """Stop the server. If the server can't be stopped even after multiple attempts then raises a ServerError"""
        if not screen.check_screen_exists(self.name):
            raise ServerError("Error: Can't stop a server that isn't running")
        jmax = 5
        try:
            jmax = min(jmax, self.module.max_stop_wait)
        except AttributeError:
            pass
        print("Will try and stop server for " + str(jmax) + " minutes")
        for j in range(jmax):
            try:
                self.module.do_stop(self, j, *args, **kwargs)
            except screen.ProcessError:
                break  # backend can't send input cross-invocation; fall through to kill
            for i in range(6):
                if not screen.check_screen_exists(self.name):
                    return  # session doesn't exist so success
                time.sleep(10)
            if not screen.check_screen_exists(self.name):
                return
            print("Server isn't stopping after " + str(j + 1) + " minutes")
        print("Killing Server")
        screen.send_to_screen(self.name, ["quit"])
        time.sleep(1)
        if screen.check_screen_exists(self.name):
            raise ServerError("Error can't kill server")

    def restart(self, *args, **kwargs):
        """Stop then start the server."""
        self.stop(*args, **kwargs)
        self.start(*args, **kwargs)

    def kill(self):
        """Force-kill the server by terminating the screen session immediately."""
        if not screen.check_screen_exists(self.name):
            raise ServerError("Error: Can't kill a server that isn't running")
        screen.send_to_screen(self.name, ["quit"])
        time.sleep(1)
        if screen.check_screen_exists(self.name):
            raise ServerError("Error: Could not kill server")
        print("Server killed")

    def status(self, *args, verbose=0, **kwargs):
        """Print the status of the server. At the least shows if there is a server screen session running"""
        if not screen.check_screen_exists(self.name):
            print("Server isn't running as no screen session")
        else:
            print("Server is running as screen session exists")
            if verbose > 0:
                self.module.status(self, verbose, *args, **kwargs)

    def connect(self):
        """Connect to the screen session to manually interact with the server"""
        screen.connect_to_screen(self.name)

    def send(self, input, **kwargs):
        """Send a line of text directly to the server console."""
        if not screen.check_screen_exists(self.name):
            raise ServerError("Error: Can't send to a server that isn't running")
        screen.send_to_server(self.name, input + "\n")

    def logs(self, lines=50, **kwargs):
        """Print the last *lines* lines of the server console log."""
        log = screen.logpath(self.name)
        if not os.path.isfile(log):
            raise ServerError("No log file found at: " + log)
        result = sp.run(["tail", "-n", str(lines), log], check=False)
        if result.returncode != 0:
            raise ServerError("Failed to read log file: " + log)

    def restore(self, backup=None, **kwargs):
        """Restore the server from a backup archive.

        With no argument, lists available backups with index numbers.
        Pass an index (int string) or the exact filename to restore that backup.
        The server is stopped automatically if it is running.
        """
        from utils.backups import backups as backup_utils

        game_dir = self.data["dir"]
        available = backup_utils.list_backups(game_dir)
        if backup is None:
            if not available:
                print("No backups found.")
                return
            for i, (tag, ts, fname) in enumerate(available):
                print(
                    "[{}]  {}  {}  ({})".format(
                        i, tag, ts.strftime("%Y-%m-%d %H:%M:%S"), fname
                    )
                )
            return
        # Resolve index or filename.
        try:
            idx = int(backup)
            if idx < 0 or idx >= len(available):
                raise ServerError(
                    "Backup index {} out of range (0–{})".format(
                        idx, len(available) - 1
                    )
                )
            filename = available[idx][2]
        except ValueError:
            filename = backup
        if screen.check_screen_exists(self.name):
            print("Stopping server before restore...")
            self.stop()
        backup_utils.restore(game_dir, filename)
        print("Restore complete: " + filename)

    def wipe(self, **kwargs):
        """Delete game-world data for this server.

        The server must not be running.  The game module must expose a
        ``wipe_paths`` attribute (list of paths relative to the game
        directory) or a ``wipe(server)`` callable; otherwise a ServerError
        is raised.
        """
        if screen.check_screen_exists(self.name):
            raise ServerError(
                "Error: Cannot wipe a running server. Stop it first."
            )
        wipe_fn = getattr(self.module, "wipe", None)
        if callable(wipe_fn):
            wipe_fn(self)
            return
        wipe_paths = getattr(self.module, "wipe_paths", None)
        if wipe_paths is None:
            raise ServerError(
                "Wipe is not supported for this server type."
            )
        game_dir = self.data["dir"]
        for rel_path in wipe_paths:
            target = os.path.join(game_dir, rel_path)
            if not os.path.exists(target):
                continue
            result = sp.run(["rm", "-rf", target], check=False)
            if result.returncode != 0:
                raise ServerError("Failed to remove: " + target)
            print("Removed: " + target)

    def query(self, **kwargs):
        """Query the game server to check whether it is responding.

        If the game module provides ``get_query_address(server)`` returning
        ``(host, port, protocol)`` that is used; otherwise the method falls
        back to a TCP ping on ``server.data["port"]``.  Protocol may be
        ``"a2s"`` (Source/Steam UDP), ``"quake"`` (Quake3/QFusion UDP),
        ``"ts3"`` (TeamSpeak 3 ServerQuery), or ``"tcp"``.
        """
        from utils import query as query_utils

        get_addr = getattr(self.module, "get_query_address", None)
        if callable(get_addr):
            host, port, protocol = get_addr(self)
            _explicit = True
        else:
            host = "127.0.0.1"
            port = self.data.get("queryport", self.data["port"])
            protocol = "a2s"
            _explicit = False

        if protocol == "a2s":
            try:
                raw = query_utils.a2s_info(host, port)
                info = query_utils.parse_a2s_info(raw)
                if info:
                    print(
                        "Server is responding (A2S on port {port}): "
                        "{name!r}  map={map!r}  "
                        "players={players}/{max_players}  game={game!r}".format(
                            port=port, **info
                        )
                    )
                else:
                    print("Server is responding (A2S query on port {}).".format(port))
                return
            except query_utils.QueryError as exc:
                if _explicit:
                    # A2S failed on the game's dedicated query port.  Try TCP on
                    # the game port (e.g. RCON or game-data TCP listener) before
                    # giving up — useful for UE4/other games in Docker CI where
                    # UDP may be unreliable but a TCP game port is still open.
                    try:
                        _game_port = self.data["port"]
                        _ms = query_utils.tcp_ping("127.0.0.1", _game_port)
                        print(
                            "Server port is open (TCP ping on port {} \u2014 {:.1f} ms).".format(
                                _game_port, _ms
                            )
                        )
                        return
                    except query_utils.QueryError:
                        pass
                    raise ServerError(
                        "Server does not appear to be responding: " + str(exc)
                    )
                # Default heuristic: fall back to TCP ping on the main game port.
                host = "127.0.0.1"
                port = self.data["port"]
                protocol = "tcp"

        if protocol == "quake":
            try:
                qinfo = query_utils.quake_status(host, port, timeout=10.0)
                print(
                    "Server is responding (Quake status on port {port}): "
                    "{name!r}  map={map!r}  "
                    "players={players}/{max_players}".format(port=port, **qinfo)
                )
                return
            except query_utils.QueryError as exc:
                raise ServerError(
                    "Server does not appear to be responding: " + str(exc)
                )

        if protocol == "ts3":
            get_creds = getattr(self.module, "get_query_credentials", None)
            login_creds = get_creds(self) if callable(get_creds) else None
            try:
                ts3info = query_utils.ts3_serverinfo(host, port, login=login_creds)
                print(
                    "Server is responding (TS3 ServerQuery on port {port}): "
                    "{name!r}  clients={clients_online}/{max_clients}".format(
                        port=port, **ts3info
                    )
                )
                return
            except query_utils.QueryError:
                # No credentials or authentication failed — fall back to a
                # plain TCP ping to confirm the ServerQuery port is reachable.
                try:
                    ms = query_utils.tcp_ping(host, port)
                    print(
                        "Server port is open (TCP ping on port {} \u2014 {:.1f} ms).".format(
                            port, ms
                        )
                    )
                    return
                except query_utils.QueryError as tcp_exc:
                    raise ServerError(
                        "Server does not appear to be responding: " + str(tcp_exc)
                    )

        # TCP ping — either explicitly requested or after A2S fallback.
        try:
            ms = query_utils.tcp_ping(host, port)
            print(
                "Server port is open (TCP ping on port {} \u2014 {:.1f} ms).".format(
                    port, ms
                )
            )
        except query_utils.QueryError as exc:
            raise ServerError("Server does not appear to be responding: " + str(exc))

    def info(self, as_json=False, detailed=False, **kwargs):
        """Retrieve detailed server information (player count, map, version, etc.).

        The game module may define ``get_info_address(server)`` returning
        ``(host, port, protocol)`` where *protocol* is ``"slp"`` (Minecraft
        Server List Ping), ``"a2s"`` (Source/Steam A2S_INFO), ``"quake"``
        (Quake3/QFusion UDP getstatus), ``"ts3"`` (TeamSpeak 3 ServerQuery),
        or ``"tcp"`` (TCP ping only).  When the hook is absent the method
        falls back to an A2S query on the game port, then TCP.

        When *as_json* is ``True`` the result is printed as a JSON object
        instead of human-readable text.  When *detailed* is ``True`` extended
        information (e.g. the TeamSpeak 3 channel list) is included.
        """
        from utils import query as query_utils

        get_addr = getattr(self.module, "get_info_address", None)
        if callable(get_addr):
            host, port, protocol = get_addr(self)
            _explicit = True
        else:
            host = "127.0.0.1"
            port = self.data.get("queryport", self.data["port"])
            protocol = "a2s"
            _explicit = False

        if protocol == "slp":
            try:
                result = query_utils.slp_info(host, port)
                if as_json:
                    print(json.dumps({"protocol": "slp", "port": port, **result}))
                    return
                print(
                    "Server info (SLP on port {port}):\n"
                    "  Description : {description}\n"
                    "  Players     : {players_online}/{players_max}\n"
                    "  Version     : {version}".format(port=port, **result)
                )
                names = result.get("player_names")
                if names:
                    print("  Online      : " + ", ".join(names))
                return
            except query_utils.QueryError as exc:
                raise ServerError("Info query failed: " + str(exc))

        if protocol == "a2s":
            try:
                raw = query_utils.a2s_info(host, port)
                parsed = query_utils.parse_a2s_info(raw)
                if parsed:
                    if as_json:
                        print(json.dumps({"protocol": "a2s", "port": port, **parsed}))
                        return
                    print(
                        "Server info (A2S on port {port}):\n"
                        "  Name        : {name}\n"
                        "  Map         : {map}\n"
                        "  Folder      : {folder}\n"
                        "  Game        : {game}\n"
                        "  App ID      : {appid}\n"
                        "  Players     : {players}/{max_players}"
                        " ({bots} bots)".format(port=port, **parsed)
                    )
                else:
                    if as_json:
                        print(json.dumps({"protocol": "a2s", "port": port}))
                        return
                    print("Server is responding (A2S on port {}), "
                          "but details could not be parsed.".format(port))
                return
            except query_utils.QueryError as exc:
                if _explicit:
                    # A2S failed on the dedicated query port — try TCP on the
                    # game port before giving up.
                    try:
                        _game_port = self.data["port"]
                        _ms = query_utils.tcp_ping("127.0.0.1", _game_port)
                        if as_json:
                            print(json.dumps({"protocol": "tcp", "port": _game_port, "latency_ms": round(_ms, 1)}))
                            return
                        print(
                            "Server port is open (TCP ping on port {} \u2014 {:.1f} ms)."
                            "  No further details available.".format(_game_port, _ms)
                        )
                        return
                    except query_utils.QueryError:
                        pass
                    raise ServerError("Info query failed: " + str(exc))
                # Default heuristic: fall through to TCP
                host = "127.0.0.1"
                port = self.data["port"]

        if protocol == "quake":
            try:
                qinfo = query_utils.quake_status(host, port, timeout=10.0)
                if as_json:
                    print(json.dumps({"protocol": "quake", "port": port, **qinfo}))
                    return
                print(
                    "Server info (Quake status on port {port}):\n"
                    "  Name       : {name}\n"
                    "  Map        : {map}\n"
                    "  Players    : {players}/{max_players}".format(port=port, **qinfo)
                )
                return
            except query_utils.QueryError as exc:
                raise ServerError("Info query failed: " + str(exc))

        if protocol == "ts3":
            get_creds = getattr(self.module, "get_query_credentials", None)
            login_creds = get_creds(self) if callable(get_creds) else None
            try:
                ts3info = query_utils.ts3_serverinfo(host, port, login=login_creds)
                channels = ts3info.get("channels", [])
                channels_count = len(channels)
                if as_json:
                    if detailed:
                        print(json.dumps({"protocol": "ts3", "port": port, **ts3info}))
                    else:
                        summary = {k: v for k, v in ts3info.items() if k != "channels"}
                        summary["channels_count"] = channels_count
                        print(json.dumps({"protocol": "ts3", "port": port, **summary}))
                    return
                print(
                    "Server info (TS3 ServerQuery on port {port}):\n"
                    "  Name     : {name}\n"
                    "  Clients  : {clients_online}/{max_clients}\n"
                    "  Version  : {version}\n"
                    "  Platform : {platform}\n"
                    "  Uptime   : {uptime}s".format(port=port, **ts3info)
                )
                if detailed:
                    if channels:
                        print("  Channels : {} channel(s)".format(channels_count))
                        for ch in channels:
                            print("    [{id}] {name}".format(**ch))
                    else:
                        print("  Channels : (none)")
                else:
                    print(
                        "  Channels : {} channel(s)  "
                        "(use --detailed to list)".format(channels_count)
                    )
                return
            except query_utils.QueryError:
                # No credentials or authentication failed — fall back to TCP ping.
                pass

        # TCP fallback
        try:
            ms = query_utils.tcp_ping(host, port)
            if as_json:
                print(json.dumps({"protocol": "tcp", "port": port, "latency_ms": round(ms, 1)}))
                return
            print(
                "Server port is open (TCP ping on port {} \u2014 {:.1f} ms)."
                "  No further details available.".format(port, ms)
            )
        except query_utils.QueryError as exc:
            raise ServerError("Server does not appear to be responding: " + str(exc))

    def dump(self):
        """Dump of the data in the data store"""
        print(self.data.prettydump())

    def doset(self, key, *args, **kwargs):
        """Set a value in the data store. The value will be check and post set actions may be run"""
        types, key = _parsekey(key)
        value = self.module.checkvalue(self, key, *args, **kwargs)
        data = self.data
        for t, el in zip(types[1:], key[:-1]):
            if el is None:
                print("Appending", el, t)
                data.append(t())
                data = data[-1]
            else:
                if isinstance(data, MappingABC) and el not in data:
                    print("Adding as absent", el, t)
                    data[el] = t()
                data = data[el]
        if value == "DELETE":
            del data[key[-1]]
        elif key[-1] is None:
            data.append(value)
        else:
            data[key[-1]] = value
        try:
            fn = self.module.postset
        except AttributeError:
            pass
        else:
            fn(server, key, *args, **kwargs)
        self.data.save()

    def activate(self, start=True):
        """Activate the server by enabling it in crontab and optionally starting it if not already running"""
        from core import program

        programpath = program.PATH
        ct = crontab.CronTab(user=True)
        jobs = (
            (job, _parsecmd(job.command.split()))
            for job in ct
            if job.is_enabled()
            and job.slices.special == "@reboot"
            and job.command.startswith(programpath)
        )
        jobs = [
            (job, cmd[1])
            for job, cmd in jobs
            if cmd[0] == programpath and cmd[2:] == ["start"]
        ]
        if any(self.name in servers for job, servers in jobs):
            print("Server is already active. Can't activate again")
        elif len(jobs) > 0:
            job, servers = jobs[0]
            servers.append(self.name)
            job.command = (
                programpath
                + " "
                + str(len(servers))
                + " "
                + " ".join(servers)
                + " start"
            )
            ct.write()
        else:
            ct.new(command=programpath + " " + self.name + " start").every_reboot()
            ct.write()
        if start and not screen.check_screen_exists(self.name):
            self.start()

    def deactivate(self, stop=True):
        """Activate the server by disabling it in crontab and optionally stopping it if it is running"""
        from core import program

        programpath = program.PATH
        if stop and screen.check_screen_exists(self.name):
            self.stop()
        ct = crontab.CronTab(user=True)
        jobs = (
            (job, _parsecmd(job.command.split()))
            for job in ct
            if job.is_enabled()
            and job.slices.special == "@reboot"
            and job.command.startswith(programpath)
        )
        jobs = [
            (job, cmd[1])
            for job, cmd in jobs
            if cmd[0] == programpath and self.name in cmd[1] and cmd[2:] == ["start"]
        ]
        if len(jobs) == 0:
            print("Server isn't active. Can't deactivate")
        else:
            for job, servers in jobs:
                if len(servers) == 1:
                    ct.remove(job)
                else:
                    servers.remove(self.name)
                    job.command = (
                        programpath
                        + " "
                        + str(len(servers))
                        + " "
                        + " ".join(servers)
                        + " start"
                    )
            ct.write()


def _parsekeyelement(el):
    """Parse one element of a dotted `set` path into a list or mapping key."""
    if el == "APPEND":
        return list, None
    elif el.isdigit():
        return list, int(el)
    else:
        return dict, str(el)


def _parsekey(key):
    """Parse a dotted `set` key into the nested elements needed for traversal."""
    return zip(*(_parsekeyelement(el) for el in key.split(".")))


def _parsecmd(cmd):
    """Parse a raw command vector into command name, server list, and arguments."""
    if cmd[1].isdigit():
        count = int(cmd[1])
        return [cmd[0], cmd[2 : 2 + count]] + cmd[2 + count :]
    return [cmd[0], [cmd[1]]] + cmd[2:]
