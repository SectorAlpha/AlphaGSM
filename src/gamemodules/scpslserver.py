"""SCP: Secret Laboratory dedicated server lifecycle helpers."""

import json
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

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
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install SCP: Secret Laboratory in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the SCP: Secret Laboratory dedicated server to the latest version.",
    "Restart the SCP: Secret Laboratory dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("servername", "contactemail", "queryport", "rconpassword")
setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname", "name"),
        description="The server's public name shown to players.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        storage_key="servername",
        native_config_key="server_name",
        examples=("AlphaGSM SCP:SL Server",),
    ),
    "contactemail": SettingSpec(
        canonical_key="contactemail",
        aliases=("email", "contact_email"),
        description="The public contact email shown in the server browser.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        storage_key="contactemail",
        native_config_key="contact_email",
        examples=("ops@example.com",),
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        aliases=("query_port",),
        description="The query port used to derive the SCP:SL query-port shift.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        storage_key="queryport",
        examples=("7778",),
    ),
    "rconpassword": SettingSpec(
        canonical_key="rconpassword",
        aliases=("querypassword", "query_administrator_password"),
        description="The administrator password used by the query/admin surface.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        storage_key="rconpassword",
        native_config_key="query_administrator_password",
        secret=True,
        examples=("changeme",),
    ),
}


def _scpsl_config_root(server):
    return os.path.join(server.data["dir"], "home", ".config", "SCP Secret Laboratory")


def _scpsl_config_dir(server):
    return os.path.join(_scpsl_config_root(server), "config")


def _scpsl_port_config_dir(server):
    return os.path.join(_scpsl_config_dir(server), str(int(server.data.get("port", 7777))))


def _scpsl_gameplay_values(server):
    port = int(server.data.get("port", 7777))
    queryport = int(server.data.get("queryport", port + 1))

    def _format_gameplay_value(spec, value):
        if spec.canonical_key == "servername":
            return str(value or "AlphaGSM {}".format(server.name))
        if spec.canonical_key == "contactemail":
            return str(value or "default")
        if spec.canonical_key == "rconpassword":
            return str(value or "alphagsmquery")
        return str(value)

    replacements = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "servername": "AlphaGSM {}".format(server.name),
            "contactemail": "default",
            "rconpassword": "alphagsmquery",
        },
        value_transform=_format_gameplay_value,
        require_explicit_key=True,
    )
    gameplay_values = {
        key_name: "{}: {}".format(key_name, value)
        for key_name, value in replacements.items()
    }
    gameplay_values["enable_query"] = "enable_query: true"
    gameplay_values["query_port_shift"] = "query_port_shift: {}".format(queryport - port)
    return gameplay_values


def _write_named_config_lines(path, replacements):
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(replacements.values()) + "\n")
        return

    with open(path, encoding="utf-8") as handle:
        existing_lines = handle.read().splitlines()

    seen = set()
    updated_lines = []
    for line in existing_lines:
        key = line.split(":", 1)[0].strip() if ":" in line else None
        if key in replacements:
            updated_lines.append(replacements[key])
            seen.add(key)
        else:
            updated_lines.append(line)
    for key in replacements:
        if key not in seen:
            updated_lines.append(replacements[key])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(updated_lines) + "\n")


def sync_server_config(server):
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
    _write_named_config_lines(gameplay_path, _scpsl_gameplay_values(server))


def configure(server, ask, port=None, dir=None, *, exe_name="LocalAdmin"):
    """Collect and store configuration values for an SCP: Secret Laboratory server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM {}".format(server.name),
            "contactemail": "",
            "rconpassword": "alphagsmquery",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["home/.config/SCP Secret Laboratory"],
        targets=["home/.config/SCP Secret Laboratory"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
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
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the SCP: Secret Laboratory server files via SteamCMD."""

    _base_install(server)
    for exe_name in ("SCPSL.x86_64", "LocalAdmin"):
        exe_path = os.path.join(server.data["dir"], exe_name)
        if os.path.isfile(exe_path):
            os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    sync_server_config(server)
    server.data.save()


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the SCP: Secret Laboratory server files and optionally restart."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the SCP: Secret Laboratory server."


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
    sync_server_config(server)
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
    sync_server_config(server)
    return (["./" + server.data["exe_name"], str(server.data["port"])], server.data["dir"])


def do_stop(server, j):
    """Stop SCP: Secret Laboratory by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed SCP: Secret Laboratory status is not implemented yet."""


def message(server, msg):
    """SCP: Secret Laboratory has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an SCP: Secret Laboratory server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported SCP: Secret Laboratory datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("queryport",),
        resolved_str_keys=("servername", "contactemail", "rconpassword"),
        raw_int_keys=("port",),
        raw_str_keys=("exe_name", "dir"),
    )


def postset(server, key, *args, **kwargs):
    """Keep derived SCP:SL gameplay config aligned after datastore edits."""

    if len(key) > 0 and str(key[0]).lower() == "port":
        sync_server_config(server)

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=_get_container_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        env={
            'HOME': runtime_module.DEFAULT_CONTAINER_WORKDIR + '/home',
            'XDG_CONFIG_HOME': runtime_module.DEFAULT_CONTAINER_WORKDIR + '/home/.config',
        },
        stdin_open=True,
)
