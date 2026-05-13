"""Space Station 14 dedicated server lifecycle helpers."""

import json
import os

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.github_releases import read_json

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

SS14_BUILDS_PAGE = "https://wizards.cdn.spacestation14.com/fork/wizards"
SS14_MANIFEST_URL = "https://wizards.cdn.spacestation14.com/fork/wizards/manifest"
SS14_SERVER_PLATFORM = "linux-x64"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Space Station 14 in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def resolve_download(version=None):
    """Resolve the latest or a specific Space Station 14 Linux x64 build."""

    manifest = read_json(SS14_MANIFEST_URL)
    builds = manifest.get("builds")
    if not isinstance(builds, dict) or not builds:
        raise ServerError("Unable to locate Space Station 14 server builds")

    if version not in (None, "", "latest"):
        resolved_version = str(version)
        build = builds.get(resolved_version)
        if not isinstance(build, dict):
            raise ServerError("Unable to locate the requested Space Station 14 server build")
    else:
        resolved_version, build = max(
            builds.items(),
            key=lambda item: item[1].get("time", "") if isinstance(item[1], dict) else "",
        )

    server_builds = build.get("server") if isinstance(build, dict) else None
    if not isinstance(server_builds, dict):
        raise ServerError("Unable to locate Space Station 14 server download metadata")
    platform_build = server_builds.get(SS14_SERVER_PLATFORM)
    if not isinstance(platform_build, dict) or not platform_build.get("url"):
        raise ServerError("Unable to locate a Linux x64 Space Station 14 server build")
    return resolved_version, platform_build["url"]


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="Robust.Server",
):
    """Collect and store configuration values for a Space Station 14 server."""

    gamemodule_common.set_server_defaults(server, {"configfile": "server_config.toml"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["data", "server_config.toml"],
        targets=["data", "server_config.toml"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=1212,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Space Station 14 server:",
    )
    gamemodule_common.configure_resolved_download_source(
        server,
        ask,
        version=version,
        url=url,
        download_name=download_name,
        resolve_download=resolve_download,
        prompt="Direct archive URL for the Space Station 14 server:",
        default_name="ss14-server.zip",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Write a managed SS14 server_config.toml from datastore values."""

    port = int(server.data.get("port", 1212))
    config_path = os.path.join(
        server.data["dir"],
        server.data.get("configfile", "server_config.toml"),
    )
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)

    lines = [
        "[log]",
        'path = "logs"',
        'format = "log_%(date)s-%(time)s.txt"',
        "level = 1",
        "enabled = false",
        "",
        "[net]",
        "tickrate = 30",
        "port = {}".format(port),
        'bindto = "::,0.0.0.0"',
        "max_connections = 256",
        "",
        "[status]",
        "enabled = true",
        "bind = {}".format(json.dumps("*:{}".format(port))),
    ]

    explicit_host = str(
        server.data.get("publicip")
        or server.data.get("externalip")
        or server.data.get("hostip")
        or server.data.get("bindaddress")
        or ""
    ).strip()
    if explicit_host and explicit_host not in {"0.0.0.0", "::"}:
        lines.append(
            "connectaddress = {}".format(
                json.dumps("udp://{}:{}".format(explicit_host, port))
            )
        )

    lines.extend(
        [
            "",
            "[game]",
            "hostname = {}".format(json.dumps("AlphaGSM {}".format(server.name))),
            "",
            "[console]",
            "loginlocal = true",
            "",
            "[hub]",
            "advertise = false",
            'tags = ""',
            'server_url = ""',
            'hub_urls = "https://hub.spacestation14.com/"',
            "",
        ]
    )

    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def install(server):
    """Download and install the Space Station 14 server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch a Space Station 14 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the SS14 Robust status API address."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "robust_status")


def get_info_address(server):
    """Return the SS14 Robust status info address."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Space Station 14 using the standard shell interrupt."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Space Station 14 status is not implemented yet."""


def message(server, msg):
    """Space Station 14 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Space Station 14 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Space Station 14 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "version"),
    )

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
