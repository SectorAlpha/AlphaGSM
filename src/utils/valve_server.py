"""Shared helpers for Steam-backed Valve-engine server modules."""

import os
import re
import inspect
from importlib import import_module
import socket
import time
from types import SimpleNamespace
from typing import NoReturn

import screen
from server.errors import ServerError
from server.settable_keys import KeyResolutionError, SettingSpec, resolve_requested_key
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.fileutils import make_empty_file
from utils.simple_kv_config import rewrite_space_config
from utils.settings import settings
import utils.steamcmd as steamcmd

STEAMCLIENT_DST = os.path.expanduser("~/.steam/sdk64/steamclient.so")
STEAMCLIENT_32_DST = os.path.expanduser("~/.steam/sdk32/steamclient.so")
_SOURCE_STATUS_PLAYERS_RE = re.compile(
    r"(?P<players>\d+) humans, (?P<bots>\d+) bots \((?P<max_players>\d+) max\)"
)
_SOURCE_BOOL_CVAR_RE = re.compile(r'"?(?P<name>[^"=]+)"?\s*=\s*"?(?P<value>[01])"?')
_SOURCE_UNKNOWN_COMMAND_RE = re.compile(r'^Unknown command "(?P<name>[^"]+)"$', re.MULTILINE)

_COMMAND_ARGS = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install the server in", str),
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
                "Restart the server after updating",
                "restart",
                None,
                True,
            ),
        )
    ),
    "restart": CmdSpec(),
}

_COMMAND_DESCRIPTIONS = {
    "update": "Update the game server to the latest version available via SteamCMD.",
    "restart": "Restart the game server by stopping it and then starting it again.",
}

VALVE_SERVER_CONFIG_SYNC_KEYS = ("servername", "rconpassword", "serverpassword")


def build_valve_server_setting_schema(
    *,
    game_name,
    default_map,
    max_players,
    servername_example=None,
    port_launch_arg_tokens=("-port",),
    map_launch_arg_tokens=("+map",),
    maxplayers_launch_arg_tokens=("-maxplayers",),
):
    """Return the shared datastore/config schema for Valve-engine servers."""

    if servername_example is None:
        servername_example = f"AlphaGSM {game_name}"

    return {
        "port": SettingSpec(
            canonical_key="port",
            description="The primary game port.",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_tokens=port_launch_arg_tokens,
            examples=("27015",),
        ),
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap", "level"),
            description="The currently selected map or level.",
            value_type="string",
            apply_to=("datastore", "launch_args"),
            storage_key="startmap",
            launch_arg_tokens=map_launch_arg_tokens,
            examples=(default_map,),
        ),
        "maxplayers": SettingSpec(
            canonical_key="maxplayers",
            aliases=("max_players",),
            description="Maximum number of player slots.",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_tokens=maxplayers_launch_arg_tokens,
            examples=(str(max_players),),
        ),
        "servername": SettingSpec(
            canonical_key="servername",
            aliases=("hostname", "server_name", "name"),
            description="The server's public name shown to players.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="hostname",
            examples=(servername_example,),
        ),
        "rconpassword": SettingSpec(
            canonical_key="rconpassword",
            aliases=("rconpass", "rcon_password"),
            description="Remote console password for administrative access.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="rcon_password",
            secret=True,
        ),
        "serverpassword": SettingSpec(
            canonical_key="serverpassword",
            aliases=("sv_password", "svpassword", "password"),
            description="Password required for players to join the server.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="sv_password",
            secret=True,
        ),
    }


def _raise_server_error(*args) -> NoReturn:
    """Raise AlphaGSM's ServerError lazily to avoid import cycles."""

    raise ServerError(*args)


def _runtime_module():
    """Import the runtime helper lazily to avoid module import cycles."""

    return import_module("server.runtime")


def _send_console_input(server, text):
    """Send console input through screen for process servers and runtime for containers."""

    runtime_name = getattr(getattr(server, "data", None), "get", lambda *_: None)("runtime")
    if runtime_name == "docker":
        return _runtime_module().send_to_server(server, text)
    return screen.send_to_server(server.name, text)


def _default_backup_config(game_dir):
    """Return a simple default backup configuration for a Valve-engine server."""

    return {
        "profiles": {"default": {"targets": [game_dir]}},
        "schedule": [("default", 0, "days")],
    }


def _default_backupfiles(game_dir, config_subdir, config_default):
    """Return the default backup target list stored in the server datastore."""

    backupfiles = [game_dir]
    if config_default:
        if config_subdir:
            backupfiles.append(os.path.join(game_dir, config_subdir, config_default))
        else:
            backupfiles.append(os.path.join(game_dir, config_default))
    return backupfiles


def integration_source_server_config():
    """Return Source-engine config overrides used only in integration tests.

    Idle SRCDS instances can hibernate fast enough that strict A2S-based
    integration checks become flaky. During integration runs, explicitly keep
    Source servers awake so `wait_for_a2s_ready()` can stay fail-fast without
    papering over readiness problems via TCP or log-only fallbacks.
    """

    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        return {}
    return {"sv_hibernate_when_empty": "0"}


def wake_source_server_for_a2s(server):
    """Nudge a Source server out of hibernation before an A2S query.

    Sending a harmless console command is enough to make affected Source
    builds tick again. If the game still allows idle hibernation, it will
    naturally return to that state once the query completes and the server is
    empty.
    """

    _send_console_input(server, "\nstatus\n")
    return 1.0


def send_console_command_and_collect_response(server, command, parser, timeout=5.0):
    """Send a console command and parse only the newly appended log output."""

    log_file = screen.logpath(server.name)
    if not os.path.isfile(log_file):
        _raise_server_error("No log file found at: " + log_file)

    with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
        handle.seek(0, os.SEEK_END)
        start_offset = handle.tell()

    _send_console_input(server, "\n{}\n".format(command.strip()))

    deadline = time.time() + timeout
    collected = ""
    with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
        handle.seek(start_offset)
        while time.time() < deadline:
            chunk = handle.read()
            if chunk:
                collected += chunk
                parsed = parser(collected)
                if parsed is not None:
                    return parsed
            time.sleep(0.1)

    parsed = parser(collected)
    if parsed is None:
        _raise_server_error(
            "Timed out waiting for console response to {!r}".format(command)
        )
    return parsed


def parse_source_console_status(output):
    """Parse the latest Source ``status`` block from console log output."""

    lines = output.splitlines()
    status_indexes = [index for index, line in enumerate(lines) if line.strip() == "status"]
    if not status_indexes:
        status_indexes = [0]

    for start in reversed(status_indexes):
        parsed = {}
        for raw_line in lines[start + 1 :]:
            line = raw_line.strip()
            if not line:
                continue
            if line == "status" and parsed:
                break
            if line.startswith("hostname:"):
                parsed["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("version :"):
                parsed["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("udp/ip  :"):
                parsed["address"] = line.split(":", 1)[1].strip()
            elif line.startswith("map     :"):
                map_value = line.split(":", 1)[1].strip()
                parsed["map"] = map_value.split(" at:", 1)[0].strip()
            elif line.startswith("players :"):
                match = _SOURCE_STATUS_PLAYERS_RE.search(line.split(":", 1)[1].strip())
                if match is not None:
                    parsed.update(
                        {
                            "players": int(match.group("players")),
                            "bots": int(match.group("bots")),
                            "max_players": int(match.group("max_players")),
                        }
                    )
            elif line.startswith("tags    :"):
                parsed["tags"] = line.split(":", 1)[1].strip()
            elif line.startswith("steamid :"):
                parsed["steamid"] = line.split(":", 1)[1].strip()

        if {"name", "version", "map", "players", "bots", "max_players"}.issubset(parsed):
            return parsed
    return None


def source_console_status(server, timeout=5.0):
    """Request and parse a Source ``status`` block from the live console."""

    return send_console_command_and_collect_response(
        server, "status", parse_source_console_status, timeout=timeout
    )


def detect_query_host(default="127.0.0.1"):
    """Return the best local IPv4 address for querying a bound game server."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            host = sock.getsockname()[0]
            if host and not host.startswith("127."):
                return host
    except OSError:
        pass
    return default


def source_query_address(server):
    """Return the preferred host/port/protocol tuple for Source A2S queries."""

    return detect_query_host(), int(server.data.get("queryport", server.data["port"])), "a2s"


def parse_source_bool_cvar(output, cvar_name):
    """Parse a Source boolean cvar response from console log output."""

    for raw_line in reversed(output.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        match = _SOURCE_BOOL_CVAR_RE.search(line)
        if match is None:
            continue
        if match.group("name").strip() != cvar_name:
            continue
        return match.group("value") == "1"
    return None


def source_hibernation_allowed(server, timeout=5.0):
    """Return whether a Source server currently allows empty-server hibernation."""

    def _parse_probe(output):
        parsed = parse_source_bool_cvar(output, "sv_hibernate_when_empty")
        if parsed is not None:
            return parsed
        for match in _SOURCE_UNKNOWN_COMMAND_RE.finditer(output):
            if match.group("name") == "sv_hibernate_when_empty":
                return "unsupported"
        return None

    probe = send_console_command_and_collect_response(
        server,
        "sv_hibernate_when_empty",
        _parse_probe,
        timeout=timeout,
    )
    if probe == "unsupported":
        return None
    return probe


def hibernating_source_console_info(server, timeout=5.0):
    """Return console status info only when the Source server looks hibernating."""

    hibernation_allowed = source_hibernation_allowed(server, timeout=timeout)
    if hibernation_allowed is False:
        return None
    parsed = source_console_status(server, timeout=timeout)
    if hibernation_allowed is True:
        return parsed
    if parsed.get("address", "").startswith("?.?.?.?:?"):
        return parsed
    return None


def _save_data_store(server):
    """Persist the server datastore when it provides a save method."""

    save = getattr(server.data, "save", None)
    if save is not None:
        save()


def _ensure_steamclient_link():
    """Link Steam's shared client libraries where Valve engines expect them."""

    for src_subdir, dst_path in (
        ("linux64", STEAMCLIENT_DST),
        ("linux32", STEAMCLIENT_32_DST),
    ):
        steamclient_src = os.path.join(steamcmd.STEAMCMD_DIR, src_subdir, "steamclient.so")
        steamclient_dir = os.path.dirname(dst_path)
        if not os.path.isfile(steamclient_src):
            continue
        if not os.path.isdir(steamclient_dir):
            os.makedirs(steamclient_dir)
        if os.path.lexists(dst_path):
            if os.path.islink(dst_path) and os.readlink(dst_path) == steamclient_src:
                continue
            os.remove(dst_path)
        os.symlink(steamclient_src, dst_path)


def updateconfig(filename, config_values):
    """Rewrite a simple key/value config file while preserving unknown lines."""

    rewrite_space_config(filename, config_values)


def validate_source_startmap(server, game_dir, startmap):
    """Validate a Source startmap against installed BSP files when available."""

    install_dir = server.data.get("dir")
    if not install_dir:
        return str(startmap)

    maps_dir = os.path.join(install_dir, game_dir, "maps")
    if not os.path.isdir(maps_dir):
        return str(startmap)

    installed_maps = sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(maps_dir)
        if filename.endswith(".bsp")
    )
    if not installed_maps:
        return str(startmap)

    normalized_maps = {name.lower(): name for name in installed_maps}
    requested_map = str(startmap)
    if requested_map.lower() in normalized_maps:
        return requested_map

    sample_maps = ", ".join(installed_maps[:10])
    raise ServerError(
        "Unsupported map %s. Installed maps include: %s"
        % (requested_map, sample_maps)
    )


def _get_module_settings(module_name):
    """Return the merged user/system settings section for a game module."""

    return settings.user.getsection("gamemodules").getsection(module_name)


def _get_int_setting(module_settings, key, default):
    """Return an integer setting while tolerating missing or blank values."""

    value = module_settings.get(key, default)
    if value in (None, ""):
        return default
    return int(value)


def define_valve_server_module(
    *,
    game_name,
    engine,
    steam_app_id,
    game_dir,
    executable,
    default_map,
    max_players,
    port=27015,
    client_port=None,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod=None,
    config_subdir="cfg",
    config_default="server.cfg",
    default_server_config=None,
    enable_map_validation=False,
):
    """Create a standard AlphaGSM game-module surface for a Valve-engine server."""
    default_port = port
    caller_globals = inspect.currentframe().f_back.f_globals
    module_name = caller_globals["__name__"].split(".")[-1]
    default_server_config = {} if default_server_config is None else default_server_config.copy()
    default_backupfiles = _default_backupfiles(game_dir, config_subdir, config_default)
    setting_schema = build_valve_server_setting_schema(
        game_name=game_name,
        default_map=default_map,
        max_players=max_players,
    )
    config_sync_keys = VALVE_SERVER_CONFIG_SYNC_KEYS

    def _server_cfg_path(server):
        """Return the authoritative config file path for this Valve server."""

        cfg_dir = os.path.join(server.data["dir"], game_dir)
        if config_subdir:
            cfg_dir = os.path.join(cfg_dir, config_subdir)
        return cfg_dir, os.path.join(cfg_dir, server.data["server_cfg"])

    def _quote_config_value(value):
        """Return a Source-style quoted config value."""

        text = str(value)
        if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
            return text
        return '"' + text.replace('"', '\\"') + '"'

    def _current_servername(server, module_settings):
        """Return the best available server name for the datastore or config file."""

        server_cfg = module_settings.getsection("servercfg")
        return server.data.get(
            "servername",
            module_settings.get(
                "servername",
                server_cfg.get("hostname", "AlphaGSM %s" % (game_name,)),
            ),
        )

    def _current_rconpassword(server, module_settings):
        """Return the best available RCON password for the datastore or config file."""

        server_cfg = module_settings.getsection("servercfg")
        return server.data.get(
            "rconpassword",
            module_settings.get("rconpassword", server_cfg.get("rcon_password", "")),
        )

    def _current_serverpassword(server, module_settings):
        """Return the best available join password for the datastore or config file."""

        server_cfg = module_settings.getsection("servercfg")
        return server.data.get(
            "serverpassword",
            module_settings.get("serverpassword", server_cfg.get("sv_password", "")),
        )

    def configure(server, ask, port=None, dir=None, *, exe_name=None):
        """Store install and networking defaults for this Valve-engine server."""
        module_settings = _get_module_settings(module_name)

        server.data["Steam_AppID"] = steam_app_id
        server.data["Steam_anonymous_login_possible"] = True
        if app_id_mod is not None:
            server.data["Steam_AppID_Mod"] = app_id_mod

        server.data.setdefault("startmap", module_settings.get("startmap", default_map))
        server.data.setdefault("maxplayers", str(module_settings.get("maxplayers", max_players)))
        server.data.setdefault("serverpassword", module_settings.get("serverpassword", ""))
        server.data.setdefault("game_dir", game_dir)
        server.data.setdefault("server_cfg", module_settings.get("server_cfg", config_default))
        server.data.setdefault("backupfiles", list(default_backupfiles))
        if "backup" not in server.data:
            server.data["backup"] = _default_backup_config(game_dir)

        if port is None:
            port = server.data.get("port", _get_int_setting(module_settings, "port", default_port))
        if ask:
            while True:
                inp = input(
                    "Please specify the port to use for this server: "
                    + ("(current=%s) " % (port,) if port is not None else "")
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
        server.data["port"] = int(port)

        if client_port is not None:
            server.data.setdefault(
                "clientport", _get_int_setting(module_settings, "clientport", client_port)
            )
        if sourcetv_port is not None:
            server.data.setdefault(
                "sourcetvport",
                _get_int_setting(module_settings, "sourcetvport", sourcetv_port),
            )
        if steam_port is not None:
            server.data.setdefault(
                "steamport", _get_int_setting(module_settings, "steamport", steam_port)
            )

        if dir is None:
            dir = (
                server.data.get("dir")
                or module_settings.get("dir")
                or os.path.expanduser(os.path.join("~", server.name))
            )
            if ask:
                inp = input(
                    "Where would you like to install the server: [%s] " % (dir,)
                ).strip()
                if inp != "":
                    dir = inp
        server.data["dir"] = os.path.join(dir, "")
        server.data["exe_name"] = (
            exe_name
            or server.data.get("exe_name")
            or module_settings.get("exe_name", executable)
        )
        _save_data_store(server)
        return (), {}

    def doinstall(server):
        """Download the server files through SteamCMD."""

        if not os.path.isdir(server.data["dir"]):
            os.makedirs(server.data["dir"])
        steamcmd.download(
            server.data["dir"],
            steam_app_id,
            True,
            validate=False,
            mod=app_id_mod,
        )

    def install(server):
        """Install the server files and create a default config if needed."""
        module_settings = _get_module_settings(module_name)

        doinstall(server)
        if server.data["exe_name"] == "srcds_run" and os.path.isfile(server.data["dir"] + "srcds_run_64"):
            server.data["exe_name"] = "srcds_run_64"

        # Strip Windows CRLF line endings from srcds startup scripts.  Some
        # older games (e.g. Insurgency) ship srcds_run with \r\n endings which
        # prevents the kernel from executing the script on Linux.
        for _script in ("srcds_run", "srcds_run.sh", os.path.join("bin", "srcds_run.sh")):
            _path = os.path.join(server.data["dir"], _script)
            if os.path.isfile(_path):
                with open(_path, "rb") as _fh:
                    _content = _fh.read()
                if _content.startswith(b"#!") and b"\r\n" in _content:
                    with open(_path, "wb") as _fh:
                        _fh.write(_content.replace(b"\r\n", b"\n"))

        cfg_dir, cfg_path = _server_cfg_path(server)
        if not os.path.isdir(cfg_dir):
            os.makedirs(cfg_dir)
        sync_server_config(server)
        _save_data_store(server)

    def sync_server_config(server):
        """Rewrite the shared Valve native config file from datastore values."""

        module_settings = _get_module_settings(module_name)
        cfg_dir, cfg_path = _server_cfg_path(server)
        if not os.path.isdir(cfg_dir):
            os.makedirs(cfg_dir)
        if not os.path.isfile(cfg_path):
            make_empty_file(cfg_path)
            with open(cfg_path, "w", encoding="utf-8") as handle:
                handle.write("// AlphaGSM default config for %s\n" % (game_name,))

        config_values = {}
        config_values.update(default_server_config)
        config_values.update(dict(module_settings.getsection("servercfg").items()))
        if engine == "source":
            config_values.update(integration_source_server_config())
        config_values["hostname"] = _quote_config_value(_current_servername(server, module_settings))
        config_values["rcon_password"] = _quote_config_value(
            _current_rconpassword(server, module_settings)
        )
        config_values["sv_password"] = _quote_config_value(
            _current_serverpassword(server, module_settings)
        )
        updateconfig(cfg_path, config_values)

    def list_setting_values(server, canonical_key):
        """Return installed values for schema-backed keys when they are enumerable."""

        if canonical_key != "map":
            return None
        install_dir = server.data.get("dir")
        if not install_dir:
            return []
        maps_dir = os.path.join(install_dir, game_dir, "maps")
        if not os.path.isdir(maps_dir):
            return []
        installed_maps = sorted(
            os.path.splitext(filename)[0]
            for filename in os.listdir(maps_dir)
            if filename.endswith(".bsp")
        )
        return installed_maps

    def prestart(server, *args, **kwargs):
        """Perform common Valve-engine startup preparation."""

        _ensure_steamclient_link()

    def update(server, validate=False, restart=False):
        """Update the server files and optionally restart the server."""

        try:
            server.stop()
        except Exception:
            print("Server has probably already stopped, updating")
        steamcmd.download(
            server.data["dir"],
            steam_app_id,
            True,
            validate=validate,
            mod=app_id_mod,
        )
        print("Server up to date")
        if restart:
            print("Starting the server up")
            server.start()

    def restart(server):
        """Restart the server process."""

        server.stop()
        server.start()

    def get_start_command(server):
        """Build the start command for this Valve-engine server."""

        exe_name = server.data["exe_name"]
        if exe_name == "srcds_run":
            for candidate in ("srcds_run_64", "srcds_run"):
                if os.path.isfile(server.data["dir"] + candidate):
                    exe_name = candidate
                    server.data["exe_name"] = candidate
                    _save_data_store(server)
                    break
        if not os.path.isfile(os.path.join(server.data["dir"], exe_name)):
            _raise_server_error("Executable file not found")
        if not exe_name.startswith("./"):
            exe_name = "./" + exe_name

        cmd = [
            exe_name,
            "-game",
            game_dir,
            "-strictportbind",
            "+ip",
            "0.0.0.0",
            "-port",
            str(server.data["port"]),
        ]
        if server.data.get("clientport") is not None:
            cmd.extend(["+clientport", str(server.data["clientport"])])
        if server.data.get("sourcetvport") is not None:
            cmd.extend(["+tv_port", str(server.data["sourcetvport"])])
        cmd.extend(
            [
                "+map",
                str(server.data["startmap"]),
                "+servercfgfile",
                str(server.data["server_cfg"]),
                "-maxplayers",
                str(server.data["maxplayers"]),
            ]
        )
        return cmd, server.data["dir"]

    def get_runtime_requirements(server):
        """Return Docker runtime metadata for Valve-engine Linux servers."""

        requirements = {
            "engine": "docker",
            "family": "steamcmd-linux",
        }
        if "dir" in server.data:
            requirements["mounts"] = [
                {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
            ]
        ports = []
        for key in ("port", "clientport", "sourcetvport", "steamport"):
            if key in server.data and server.data[key] is not None:
                ports.append(
                    {
                        "host": int(server.data[key]),
                        "container": int(server.data[key]),
                        "protocol": "udp",
                    }
                )
        if ports:
            requirements["ports"] = ports
        return requirements

    def get_container_spec(server):
        """Return the Docker launch spec for this Valve-engine server."""

        cmd, _cwd = get_start_command(server)
        requirements = get_runtime_requirements(server)
        return {
            "working_dir": "/srv/server",
            "stdin_open": True,
            "mounts": requirements.get("mounts", []),
            "ports": requirements.get("ports", []),
            "command": cmd,
        }

    def do_stop(server, j):
        """Send the generic Valve-engine shutdown command."""

        _send_console_input(server, "\nquit\n")

    def status(server, verbose):
        """Detailed engine-specific status is not implemented yet."""
        return None

    def message(server, msg):
        """Broadcast a message using the generic Valve-engine chat command."""

        _send_console_input(server, "\nsay %s\n" % (msg,))

    def backup(server, profile=None):
        """Run the shared backup helper against the install directory."""

        backup_utils.backup(server.data["dir"], server.data["backup"], profile)

    def checkvalue(server, key, *value):
        """Validate data-store edits for the shared Valve-engine module."""

        if len(key) == 0:
            _raise_server_error("Invalid key")
        if key[0] == "backup":
            return backup_utils.checkdatavalue(server.data["backup"], key, *value)
        if len(value) == 0:
            _raise_server_error("No value specified")
        try:
            resolved = resolve_requested_key(key[0], setting_schema)
        except KeyResolutionError:
            resolved = None
        if resolved is not None:
            if resolved.canonical_key == "port":
                return int(value[0])
            if resolved.canonical_key == "maxplayers":
                return str(int(value[0]))
            if resolved.canonical_key in ("servername", "rconpassword", "serverpassword"):
                return str(value[0])
            if resolved.canonical_key == "map":
                if enable_map_validation and engine == "source":
                    return validate_source_startmap(server, game_dir, value[0])
                return str(value[0])
        if key[0] in ("port", "clientport", "sourcetvport", "steamport"):
            return int(value[0])
        if key[0] == "maxplayers":
            return str(int(value[0]))
        if key[0] in ("servername", "hostname"):
            return str(value[0])
        if key[0] in ("rconpassword", "rcon_password"):
            return str(value[0])
        if key[0] in ("serverpassword", "sv_password", "svpassword", "password"):
            return str(value[0])
        if key[0] == "startmap":
            if enable_map_validation and engine == "source":
                return validate_source_startmap(server, game_dir, value[0])
            return str(value[0])
        if key[0] in ("dir", "server_cfg", "exe_name"):
            return str(value[0])
        _raise_server_error("Unsupported key for Valve server module: %s" % (key[0],))

    exported_namespace = SimpleNamespace(
        steam_app_id=steam_app_id,
        commands=("update", "restart"),
        command_args=_COMMAND_ARGS,
        command_descriptions=_COMMAND_DESCRIPTIONS,
        command_functions={"update": update, "restart": restart},
        max_stop_wait=1,
        configure=configure,
        install=install,
        doinstall=doinstall,
        prestart=prestart,
        update=update,
        restart=restart,
        get_start_command=get_start_command,
        get_runtime_requirements=get_runtime_requirements,
        get_container_spec=get_container_spec,
        do_stop=do_stop,
        status=status,
        message=message,
        backup=backup,
        checkvalue=checkvalue,
        config_sync_keys=config_sync_keys,
        sync_server_config=sync_server_config,
        setting_schema=setting_schema,
        list_setting_values=list_setting_values,
        updateconfig=updateconfig,
        wake_a2s_query=wake_source_server_for_a2s if engine == "source" else None,
        get_query_address=source_query_address if engine == "source" else None,
        get_info_address=source_query_address if engine == "source" else None,
        get_hibernating_console_info=(
            hibernating_source_console_info if engine == "source" else None
        ),
    )
    caller_globals["config_sync_keys"] = config_sync_keys
    caller_globals["sync_server_config"] = sync_server_config
    caller_globals["setting_schema"] = setting_schema
    caller_globals["list_setting_values"] = list_setting_values
    return exported_namespace
