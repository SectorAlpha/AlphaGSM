"""PaperMC-specific setup and install helpers."""

from .custom import *
from . import custom as cust
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
                "Minecraft version to download. Uses the latest stable build by default.",
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
    eula=None,
    version=None,
    url=None,
    exe_name="paper.jar",
    download_name="paper.jar"
):
    """Collect configuration values for a PaperMC server."""

    if url is None:
        resolved_version, url = resolve_download("paper", version=version)
        server.data["version"] = resolved_version
    else:
        server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = download_name
    return cust.configure(server, ask, port, dir, eula=eula, exe_name=exe_name)


def install(server, *, eula=False):
    """Download or validate the configured PaperMC server jar."""

    install_downloaded_jar(server)
    cust.install(server, eula=eula)
