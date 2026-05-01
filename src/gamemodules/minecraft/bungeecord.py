"""Bungeecord-specific setup and runtime helpers."""

import os
from pathlib import Path
import urllib.request
import json
import time
import datetime
import subprocess as sp
import re
import screen
import server.runtime as runtime_module
import downloader
from server.modsupport.downloads import download_to_cache
from server import ServerError
from server.modsupport.plugin_jars import build_plugin_jar_mod_support
from server.modsupport.providers import resolve_direct_url_entry, resolve_moddb_entry
from server.modsupport.registry import CuratedRegistryLoader
import utils.updatefs
from utils.cmdparse.cmdspec import CmdSpec, OptSpec, ArgSpec
from utils.gamemodules import common as gamemodule_common

command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
        )
    ),
}
command_descriptions = {}
command_functions = {}


# Regex to locate the first listener's host line in config.yml
_BUNGEE_HOST_RE = re.compile(r'^(\s*host:\s*)(\S+):(\d+)', re.MULTILINE)
_CONFIG_GENERATION_TIMEOUT = 120
ALLOWED_PROXY_PLUGIN_DESTINATIONS = ("plugins",)
DEFAULT_PROXY_MOD_CACHE_DIRNAME = "minecraft-bungeecord"
VELOCITY_PROXY_MOD_CACHE_DIRNAME = "minecraft-velocity"


def _default_proxy_curated_registry_path(server=None):
    if server is not None and server.data.get("mod_cache_dirname") == VELOCITY_PROXY_MOD_CACHE_DIRNAME:
        return Path(__file__).with_name("curated_velocity_plugins.json")
    return Path(__file__).with_name("curated_proxy_plugins.json")


def load_proxy_curated_registry(server=None):
    """Load the checked-in proxy plugin registry or an override file."""

    override = os.environ.get("ALPHAGSM_PROXY_CURATED_MODS_PATH")
    path = Path(override) if override else _default_proxy_curated_registry_path(server)
    return CuratedRegistryLoader.load(path)


def _mod_label(server):
    return server.data.get("mod_label", "BungeeCord")


MOD_SUPPORT = build_plugin_jar_mod_support(
    game_label="proxy",
    curated_registry_loader=load_proxy_curated_registry,
    cache_namespace_getter=lambda server: server.data.get(
        "mod_cache_dirname", DEFAULT_PROXY_MOD_CACHE_DIRNAME
    ),
    runtime_label_getter=_mod_label,
    download_to_cache_getter=lambda: download_to_cache,
    resolve_direct_url_entry_getter=lambda: resolve_direct_url_entry,
    resolve_moddb_entry_getter=lambda: resolve_moddb_entry,
)
commands = MOD_SUPPORT.commands
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions.update(MOD_SUPPORT.command_functions)
ensure_mod_state = MOD_SUPPORT.ensure_mod_state
apply_configured_mods = MOD_SUPPORT.apply_configured_mods
cleanup_configured_mods = MOD_SUPPORT.cleanup_configured_mods
bungeecord_mod_command = MOD_SUPPORT.command_functions["mod"]


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="BungeeCord.jar",
    mod_cache_dirname=DEFAULT_PROXY_MOD_CACHE_DIRNAME,
    mod_label="BungeeCord"
):
    """Collect and store configuration values for a Bungeecord server."""
    if port is None:
        port = server.data.get("port", 25565)
    server.data["port"] = int(port)

    if dir is None:
        dir = runtime_module.suggest_install_dir(server, server.data.get("dir"))
        if ask:
            inp = input(
                "Where would you like to install the minecraft server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = dir

    if not "exe_name" in server.data:
        server.data["exe_name"] = exe_name
    server.data.setdefault("mod_cache_dirname", mod_cache_dirname)
    server.data.setdefault("mod_label", mod_label)
    ensure_mod_state(server)
    server.data.save()

    return (), {}


def install(server, *, eula=False):
    """Install or validate the Bungeecord server files for this server."""
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    mcjar = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(mcjar):
        raise ServerError(
            "Can't find server jar ({}). Please place the files in the directory and/or update the 'exe_name' then run setup again".format(
                mcjar
            )
        )
    config_file = os.path.join(server.data["dir"], "config.yml")
    if not os.path.isfile(config_file):
        javapath = server.data.get("javapath", "java")
        print("Running server briefly to generate config.yml …")
        proc = sp.Popen(
            [javapath, "-Xmx256M", "-jar", server.data["exe_name"]],
            cwd=server.data["dir"],
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
        )
        deadline = time.time() + _CONFIG_GENERATION_TIMEOUT
        try:
            while time.time() < deadline and not os.path.isfile(config_file):
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
    if os.path.isfile(config_file):
        _update_bungee_host_port(config_file, server.data.get("port", 25565))
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)
    else:
        server.data.save()


def _update_bungee_host_port(config_path, port):
    """Update the first listener host entry in a BungeeCord/Waterfall config.yml."""
    with open(config_path, "r") as fh:
        content = fh.read()
    updated = _BUNGEE_HOST_RE.sub(
        lambda m: m.group(1) + m.group(2) + ":" + str(port),
        content,
        count=1,
    )
    with open(config_path, "w") as fh:
        fh.write(updated)


def get_start_command(server):
    """Build the command list used to launch the Bungeecord server."""
    return ["java", "-Xmx256M", "-jar", server.data["exe_name"]], server.data["dir"]


def get_runtime_requirements(server):
    """Return Docker runtime metadata for Java-based Minecraft proxies."""

    java_major = int(server.data.get("java_major", 17))
    requirements = {
        "engine": "docker",
        "family": "java",
        "java": java_major,
        "env": {
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "BungeeCord.jar"),
        },
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "tcp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Java-based Minecraft proxies."""

    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            'exec java -Xmx256M -jar "$ALPHAGSM_SERVER_JAR"',
        ],
    }


def do_stop(server, j):
    """Send the console command used to stop a running Bungeecord server."""
    runtime_module.send_to_server(server, "\nend\n")


def status(server, verbose):
    """Report Bungeecord server status information."""
    pass


def message(server, msg):
    """Explain that Bungeecord has no direct user-message support here."""

    gamemodule_common.print_unsupported_message("This server doesn't have users directly")


def checkvalue(server, key, value):
    """Validate a proposed stored setting value for this server type."""
    if key == "exe_name":
        return value
    raise ServerError("All read only as not yet implemented")


def backup(server):
    """Explain that this server type has no dedicated backup implementation here."""
    print("This server doesn't have anything to backup")


def get_info_address(server):
    """Return the SLP address for the ``info`` command.

    BungeeCord-based proxies (BungeeCord, Waterfall, Velocity) implement
    Minecraft's Server List Ping protocol on their main TCP port.
    """
    return (runtime_module.resolve_query_host(server), server.data["port"], "slp")


def get_query_address(server):
    """Return the TCP endpoint used by the ``query`` command."""

    return (runtime_module.resolve_query_host(server), server.data["port"], "tcp")
