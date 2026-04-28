"""Waterfall-specific setup and install helpers."""

from .bungeecord import *
from . import bungeecord as proxy_base
from .papermc import resolve_download
from utils.cmdparse.cmdspec import CmdSpec, OptSpec
from utils.gamemodules.minecraft.jardownload import install_downloaded_jar


import server.runtime as runtime_module

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

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env=requirements.get("env", {}),
        stdin_open=True,
        tty=True,
    )


def status(server, verbose):
    """Report Waterfall proxy status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
