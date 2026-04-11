"""SCP: Secret Laboratory dedicated server lifecycle helpers."""

import json
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 996560
steam_anonymous_login_possible = True
LOCALADMIN_GLOBAL_CONFIG = """restart_on_crash: true
enable_heartbeat: true
set_terminal_title: true
la_live_view_use_utc: false
la_live_view_time_format: yyyy-MM-dd HH:mm:ss.fff zzz
la_show_stdout_and_stderr: false
la_no_set_cursor: true
enable_true_color: true
enable_la_logs: true
la_logs_use_utc: false
la_logs_use_Z_for_utc: false
la_log_auto_flush: true
la_log_stdout_and_stderr: true
la_delete_old_logs: true
la_logs_expiration_days: 90
delete_old_round_logs: false
round_logs_expiration_days: 180
compress_old_round_logs: false
round_logs_compression_threshold_days: 14
heartbeat_span_max_threshold: 30
heartbeat_restart_in_seconds: 11
la_to_sl_buffer_size: 25000
sl_to_la_buffer_size: 200000
"""

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install SCP: Secret Laboratory in", str),
        )
    ),
    "update": CmdSpec(
        options=(
            OptSpec("v", ["validate"], "Validate the server files after updating", "validate", None, True),
            OptSpec("r", ["restart"], "Restart the server after updating", "restart", None, True),
        )
    ),
    "restart": CmdSpec(),
}
command_descriptions = {
    "update": "Update the SCP: Secret Laboratory dedicated server to the latest version.",
    "restart": "Restart the SCP: Secret Laboratory dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def _scpsl_config_root(server):
    return os.path.join(server.data["dir"], "home", ".config", "SCP Secret Laboratory")


def _scpsl_config_dir(server):
    return os.path.join(_scpsl_config_root(server), "config")


def _scpsl_port_config_dir(server):
    return os.path.join(_scpsl_config_dir(server), str(server.data["port"]))


def _seed_localadmin_files(server):
    config_dir = _scpsl_config_dir(server)
    port_config_dir = _scpsl_port_config_dir(server)
    internal_dir = os.path.join(_scpsl_config_root(server), "internal")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(port_config_dir, exist_ok=True)
    os.makedirs(internal_dir, exist_ok=True)

    localadmin_data_path = os.path.join(config_dir, "localadmin_internal_data.json")
    if not os.path.isfile(localadmin_data_path):
        with open(localadmin_data_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "GitHubPersonalAccessToken": None,
                    "EulaAccepted": "2026-04-04T07:56:13.8569381Z",
                    "PluginManagerWarningDismissed": False,
                    "LastPluginAliasesRefresh": None,
                },
                handle,
                separators=(",", ":"),
            )

    global_config_path = os.path.join(config_dir, "config_localadmin_global.txt")
    if not os.path.isfile(global_config_path):
        with open(global_config_path, "w", encoding="utf-8") as handle:
            handle.write(LOCALADMIN_GLOBAL_CONFIG)

    gameplay_path = os.path.join(port_config_dir, "config_gameplay.txt")
    gameplay_lines = [
        "server_name: AlphaGSM {}".format(server.name),
        "contact_email: {}".format(server.data.get("contactemail", "default") or "default"),
        "enable_query: true",
        "query_port_shift: 1",
        "query_administrator_password: alphagsmquery",
    ]
    if not os.path.isfile(gameplay_path):
        with open(gameplay_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(gameplay_lines) + "\n")
    else:
        with open(gameplay_path, encoding="utf-8") as handle:
            existing_lines = handle.read().splitlines()
        replacements = {
            "server_name": gameplay_lines[0],
            "contact_email": gameplay_lines[1],
            "enable_query": gameplay_lines[2],
            "query_port_shift": gameplay_lines[3],
            "query_administrator_password": gameplay_lines[4],
        }
        seen = set()
        updated_lines = []
        for line in existing_lines:
            key = line.split(":", 1)[0].strip() if ":" in line else None
            if key in replacements:
                updated_lines.append(replacements[key])
                seen.add(key)
            else:
                updated_lines.append(line)
        for key in (
            "server_name",
            "contact_email",
            "enable_query",
            "query_port_shift",
            "query_administrator_password",
        ):
            if key not in seen:
                updated_lines.append(replacements[key])
        with open(gameplay_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(updated_lines) + "\n")


def configure(server, ask, port=None, dir=None, *, exe_name="LocalAdmin"):
    """Collect and store configuration values for an SCP: Secret Laboratory server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("contactemail", "")
    server.data.setdefault("backupfiles", ["home/.config/SCP Secret Laboratory"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["home/.config/SCP Secret Laboratory"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 7777)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    server.data["queryport"] = int(server.data.get("queryport", server.data["port"] + 1))

    if dir is None:
        dir = runtime_module.suggest_install_dir(server, server.data.get("dir"))
        if ask:
            inp = input(
                "Where would you like to install the SCP: Secret Laboratory server: [%s] "
                % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the SCP: Secret Laboratory server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    for exe_name in ("SCPSL.x86_64", "LocalAdmin"):
        exe_path = os.path.join(server.data["dir"], exe_name)
        if os.path.isfile(exe_path):
            os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    _seed_localadmin_files(server)
    server.data.save()


def update(server, validate=False, restart=False):
    """Update the SCP: Secret Laboratory server files and optionally restart."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the SCP: Secret Laboratory server."""

    server.stop()
    server.start()


def get_query_address(server):
    """Return the SCP:SL TCP query endpoint when query is enabled."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "tcp")


def get_info_address(server):
    """Return the SCP:SL TCP info endpoint when query is enabled."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch an SCP: Secret Laboratory dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    _seed_localadmin_files(server)
    home_dir = os.path.join(server.data["dir"], "home")
    xdg_config_home = os.path.join(home_dir, ".config")
    return (
        [
            "env",
            "HOME=" + home_dir,
            "XDG_CONFIG_HOME=" + xdg_config_home,
            "./" + server.data["exe_name"],
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def _get_container_start_command(server):
    """Build the Docker launch command for SCP:SL using container-local paths."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    _seed_localadmin_files(server)
    return (["./" + server.data["exe_name"], str(server.data["port"])], server.data["dir"])


def do_stop(server, j):
    """Stop SCP: Secret Laboratory by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed SCP: Secret Laboratory status is not implemented yet."""


def message(server, msg):
    """SCP: Secret Laboratory has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an SCP: Secret Laboratory server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported SCP: Secret Laboratory datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport"):
        return int(value[0])
    if key[0] in ("exe_name", "dir", "contactemail"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=_get_container_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        env={
            'HOME': runtime_module.DEFAULT_CONTAINER_WORKDIR + '/home',
            'XDG_CONFIG_HOME': runtime_module.DEFAULT_CONTAINER_WORKDIR + '/home/.config',
        },
        stdin_open=True,
    )
