"""Velocity Proxy-specific setup and install helpers."""

import os
import re
import subprocess as sp
import time

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
                "Velocity version to download. Uses the latest stable build by default.",
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


# Regex to update the bind address in velocity.toml
_VELOCITY_BIND_RE = re.compile(r'^(bind\s*=\s*)"[^"]*"', re.MULTILINE)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="velocity.jar",
    download_name="velocity.jar"
):
    """Collect configuration values for a Velocity proxy server."""

    if url is None:
        resolved_version, url = resolve_download("velocity", version=version)
        server.data["version"] = resolved_version
    else:
        server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = download_name
    return proxy_base.configure(server, ask, port=port, dir=dir, exe_name=exe_name)


def install(server, *, eula=False):
    """Download or validate the configured Velocity proxy jar."""

    install_downloaded_jar(server)
    proxy_base.install(server)
    # Velocity uses velocity.toml instead of config.yml - update its bind address.
    server_dir = server.data.get("dir")
    if not server_dir:
        return
    velocity_toml = os.path.join(server_dir, "velocity.toml")
    if not os.path.isfile(velocity_toml):
        javapath = server.data.get("javapath", "java")
        print("Running Velocity briefly to generate velocity.toml …")
        proc = sp.Popen(
            [javapath, "-Xmx256M", "-jar", server.data["exe_name"]],
            cwd=server.data["dir"],
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
        )
        deadline = time.time() + 30
        try:
            while time.time() < deadline and not os.path.isfile(velocity_toml):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except sp.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    if os.path.isfile(velocity_toml):
        _update_velocity_bind_port(velocity_toml, server.data.get("port", 25577))


def _update_velocity_bind_port(toml_path, port):
    """Update the bind address line in velocity.toml."""
    with open(toml_path, "r") as fh:
        content = fh.read()
    updated = _VELOCITY_BIND_RE.sub(
        f'\\1"0.0.0.0:{port}"',
        content,
        count=1,
    )
    with open(toml_path, "w") as fh:
        fh.write(updated)

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
    """Report Velocity proxy status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
