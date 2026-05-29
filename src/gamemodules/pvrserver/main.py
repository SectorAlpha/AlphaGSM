"""Pavlov VR dedicated server lifecycle helpers."""

import os
import shlex
import subprocess as sp

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 622970
steam_anonymous_login_possible = True
DEFAULT_PORT = 7777
STATUS_PORT_OFFSET = 400

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Pavlov VR in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Pavlov VR dedicated server to the latest version.",
    "Restart the Pavlov VR dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-PORT={value}",
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="Steam query port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-QueryPort={value}",
    ),
    "map": SettingSpec(
        canonical_key="map",
        description="Initial map or workshop scenario.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Map={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="PavlovServer.sh"):
    """Collect and store configuration values for a Pavlov VR server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"map": "UGC1664/SND"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Pavlov", "Saved"],
        targets=["Pavlov", "Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=DEFAULT_PORT,
        prompt="Please specify the port to use for this server:",
    )
    server.data["queryport"] = str(_status_port(server))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Pavlov VR server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
_shared_install = install


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
_shared_update = update


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Pavlov VR server."


def _status_port(server):
    return int(server.data.get("port", DEFAULT_PORT)) + STATUS_PORT_OFFSET


def _exe_path(server):
    return os.path.join(server.data["dir"], server.data["exe_name"])


def _recoverable_steamcmd_false_negative(server, ex):
    output = getattr(ex, "output", "") or ""
    return (
        "state is 0x602 after update job." in output
        and os.path.isfile(_exe_path(server))
    )


def install(server):
    """Download the Pavlov VR server files via SteamCMD."""

    try:
        _shared_install(server)
    except sp.CalledProcessError as ex:
        if not _recoverable_steamcmd_false_negative(server, ex):
            raise


def update(server, validate=False, restart=False):
    """Update the Pavlov VR server files and optionally restart the server."""

    try:
        _shared_update(server, validate=validate, restart=restart)
    except sp.CalledProcessError as ex:
        if not _recoverable_steamcmd_false_negative(server, ex):
            raise
        print("Server up to date")
        if restart:
            print("Starting the server up")
            server.start()


def get_query_address(server):
    """Pavlov VR uses Steam A2S on the dedicated query port."""
    return (runtime_module.resolve_query_host(server), _status_port(server), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""
    return (runtime_module.resolve_query_host(server), _status_port(server), "a2s")


def get_start_command(server):
    """Build the command used to launch a Pavlov VR dedicated server."""

    exe_path = _exe_path(server)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {
            "port": setting_schema["port"],
            "map": setting_schema["map"],
        },
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *dynamic_args],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Pavlov VR by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Pavlov VR status is not implemented yet."""



def message(server, msg):
    """Pavlov VR has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Pavlov VR server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Pavlov VR datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("map", "exe_name", "dir"),
        backup_module=backup_utils,
    )


def get_runtime_requirements(server):
    """Expose the gameplay port plus Pavlov's fixed status-helper port."""

    server.data["queryport"] = str(_status_port(server))
    return gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=(
            {'key': 'port', 'protocol': 'udp'},
            {'key': 'port', 'protocol': 'tcp'},
            {'key': 'queryport', 'protocol': 'udp'},
            {'key': 'queryport', 'protocol': 'tcp'},
        ),
        extra={
            "host_dependencies": [
                {
                    "id": "libcxx",
                    "display_name": "LLVM libc++ runtime",
                    "kind": "shared-library",
                    "library_names": {
                        "linux": "libc++.so.1",
                    },
                    "install_hints": {
                        "linux": "Install the host package 'libc++1' before launching Pavlov VR locally.",
                        "macos": "Install the Apple or Homebrew LLVM libc++ runtime before launching Pavlov VR locally.",
                        "windows": "Install the required C++ runtime before launching Pavlov VR locally on Windows.",
                    },
                }
            ]
        },
    )(server)


def get_container_spec(server):
    """Publish the gameplay port plus Pavlov's fixed status-helper port."""

    server.data["queryport"] = str(_status_port(server))
    requirements = get_runtime_requirements(server)
    command, _cwd = get_start_command(server)
    if not any(arg.startswith("-QueryPort=") for arg in command[1:]):
        command.append("-QueryPort=" + str(server.data["queryport"]))
    shell_command = " ".join(shlex.quote(part) for part in command)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "tty": False,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            "getent passwd pavlov >/dev/null 2>&1 || "
            "useradd -m -d /home/pavlov -s /bin/bash pavlov; "
            "mkdir -p /home/pavlov/.config && "
            "chown -R pavlov:pavlov /home/pavlov /srv/server && "
            "export HOME=/home/pavlov USER=pavlov LOGNAME=pavlov "
            "XDG_CONFIG_HOME=/home/pavlov/.config && "
            "exec setpriv --reuid=$(id -u pavlov) --regid=$(id -g pavlov) "
            "--clear-groups "
            + shell_command,
        ],
    }
