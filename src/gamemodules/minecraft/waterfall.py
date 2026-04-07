"""Waterfall-specific setup and install helpers."""

from .bungeecord import *
from . import bungeecord as proxy_base
from .jardownload import install_downloaded_jar
from .papermc import resolve_download
from utils.cmdparse.cmdspec import CmdSpec, OptSpec


command_args = command_args.copy()
command_args["setup"] = command_args["setup"].combine(
    CmdSpec(
        options=(
            OptSpec(
                "v",
                ["version"],
                "Waterfall version to download. Uses the latest stable build by default.",
                "version",
                "VERSION",
                str,
            ),
            OptSpec(
                "u",
                ["url"],
                "Download URL to use instead of the PaperMC downloads service.",
                "url",
                "URL",
                str,
            ),
        )
    )
)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="waterfall.jar",
    download_name="waterfall.jar"
):
    """Collect configuration values for a Waterfall proxy server."""

    if url is None:
        resolved_version, url = resolve_download("waterfall", version=version)
        server.data["version"] = resolved_version
    else:
        server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = download_name
    return proxy_base.configure(server, ask, port=port, dir=dir, exe_name=exe_name)


def install(server, *, eula=False):
    """Download or validate the configured Waterfall proxy jar."""

    install_downloaded_jar(server)
    proxy_base.install(server)
