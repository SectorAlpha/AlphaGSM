"""TShock server module for Terraria."""

import server.runtime as runtime_module

from .common import (
    backup,
    checkvalue,
    command_args,
    command_descriptions,
    command_functions,
    commands,
    configure_base,
    do_stop,
    get_tshock_start_command,
    install_archive,
    message,
    resolve_tshock_download,
    status,
)
from utils.gamemodules import common as gamemodule_common


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="TShock.Server.dll",
    download_name="tshock.zip"
):
    """Collect and store configuration values for a TShock server."""

    if url is None:
        version, url = resolve_tshock_download()
    return configure_base(
        server,
        ask,
        port,
        dir,
        exe_name=exe_name,
        version=version,
        url=url,
        download_name=download_name,
        max_players=8,
        world_name=server.name,
        world_size=2,
        backupfiles=("Worlds", "serverconfig.txt", "tshock"),
        java_runtime="dotnet",
    )


def install(server):
    """Download and install the TShock server files."""

    install_archive(server)


def get_start_command(server):
    """Build the start command for TShock."""

    return get_tshock_start_command(server)

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
