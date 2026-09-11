"""Unreal Tournament 3 dedicated server lifecycle helpers."""

import os

from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The port to use for the Unreal Tournament 3 server",
    "The directory containing the Unreal Tournament 3 server files",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _configfile(server):
    return server.data.get("configfile") or "UTGame/Config/{}/UTGame.ini".format(server.name)


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/ut3"):
    """Collect and store configuration values for an Unreal Tournament 3 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "ip": "0.0.0.0",
            "queryport": "6500",
            "defaultmap": "VCTF-Suspense",
            "game": "UTGameContent.UTVehicleCTFGame_Content",
            "mutators": "",
            "isdedicated": "true",
            "islanmatch": "false",
            "usesstats": "false",
            "shouldadvertise": "true",
            "pureserver": "1",
            "allowjoininprogress": "true",
            "gsusername": "",
            "gspassword": "",
            "configfile": "UTGame/Config/{}/UTGame.ini".format(server.name),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Binaries", "UTGame"],
        targets=["Binaries", "UTGame"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", "6500")
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where are the Unreal Tournament 3 server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """UT3 uses user-provided files; validate that the dedicated binary is staged."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "ut3server",
            "an owned Unreal Tournament 3 dedicated server install",
            actions=(
                "Copy the UT3 dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Set gsusername and gspassword as needed if you want OpenSpy-authenticated advertising",
                "Retry setup once the staged server tree is present",
            ),
            docs_slug="ut3server",
        )


def get_start_command(server):
    """Build the command used to launch an Unreal Tournament 3 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "ut3server",
            "an owned Unreal Tournament 3 dedicated server install",
            actions=(
                "Copy the UT3 dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Set gsusername and gspassword as needed if you want OpenSpy-authenticated advertising",
                "Retry start after the staged server tree is present",
            ),
            docs_slug="ut3server",
        )
    travel_arg = gamemodule_common.build_unreal_travel_arg(
        server.data.get("defaultmap", "VCTF-Suspense"),
        options=(
            ("Game", server.data.get("game", "UTGameContent.UTVehicleCTFGame_Content")),
            ("bIsDedicated", server.data.get("isdedicated", "true")),
            ("bIsLanMatch", server.data.get("islanmatch", "false")),
            ("bUsesStats", server.data.get("usesstats", "false")),
            ("bShouldAdvertise", server.data.get("shouldadvertise", "true")),
            ("PureServer", server.data.get("pureserver", "1")),
            ("bAllowJoinInProgress", server.data.get("allowjoininprogress", "true")),
            ("ConfigSubDir", server.name),
        ),
        optional_options=(("Mutator", server.data.get("mutators", "")),),
    )
    return (
        [
            "./" + server.data["exe_name"],
            "server",
            travel_arg,
            "-login={}".format(server.data.get("gsusername", "")),
            "-password={}".format(server.data.get("gspassword", "")),
            "-multihome={}".format(server.data.get("ip", "0.0.0.0")),
            "-port={}".format(server.data["port"]),
            "-queryport={}".format(server.data.get("queryport", "6500")),
            "-nohomedir",
            "-unattended",
            "-log=server.log",
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the Unreal3/GameSpy4 query address for UT3."""

    return runtime_module.resolve_query_host(server), int(server.data.get("queryport", 6500)), "ut3"


def get_info_address(server):
    """Return the Unreal3/GameSpy4 info address for UT3."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Unreal Tournament 3 by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Unreal Tournament 3 status is not implemented yet."""


def message(server, msg):
    """Unreal Tournament 3 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Unreal Tournament 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Unreal Tournament 3 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=(
            "exe_name",
            "dir",
            "ip",
            "defaultmap",
            "game",
            "mutators",
            "isdedicated",
            "islanmatch",
            "usesstats",
            "shouldadvertise",
            "pureserver",
            "allowjoininprogress",
            "gsusername",
            "gspassword",
            "configfile",
        ),
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
    ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
    ),
    stdin_open=True,
)
