"""Terraria vanilla server module."""

from .common import (
    backup,
    checkvalue,
    command_args,
    command_descriptions,
    command_functions,
    commands,
    configure_base,
    do_stop,
    get_vanilla_start_command,
    install_archive,
    message,
    resolve_terraria_download,
    status,
)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="Linux/TerrariaServer.bin.x86_64",
    download_name="terraria-server.zip"
):
    """Collect and store configuration values for a Terraria vanilla server."""

    if url is None:
        version, url = resolve_terraria_download(version=version)
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
        backupfiles=("Worlds", "serverconfig.txt", "banlist.txt"),
    )


def install(server):
    """Download and install the Terraria vanilla server files."""

    install_archive(server)


def get_start_command(server):
    """Build the start command for Terraria vanilla."""

    return get_vanilla_start_command(server)
