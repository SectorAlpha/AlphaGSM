"""PaperMC-specific setup and install helpers."""

from pathlib import Path

from .custom import *
from . import custom as cust
from .papermc import resolve_download
from server.modsupport.downloads import download_to_cache
from server.modsupport.plugin_jars import build_plugin_jar_mod_support
from server.modsupport.providers import resolve_direct_url_entry, resolve_moddb_entry
from server.modsupport.registry import CuratedRegistryLoader
from utils.cmdparse.cmdspec import CmdSpec, OptSpec
from utils.gamemodules.minecraft.jardownload import install_downloaded_jar


import server.runtime as runtime_module

commands = commands + ("mod",)
command_args = command_args.copy()
command_descriptions = command_descriptions.copy()
command_functions = command_functions.copy()

PAPER_MOD_CACHE_DIRNAME = "minecraft-paper"

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
def load_paper_curated_registry(server=None):
    """Load the checked-in Paper plugin registry or an override file."""

    del server
    override = os.environ.get("ALPHAGSM_PAPER_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_paper_plugins.json")
    return CuratedRegistryLoader.load(path)
MOD_SUPPORT = build_plugin_jar_mod_support(
    game_label="Paper",
    curated_registry_loader=load_paper_curated_registry,
    cache_namespace=PAPER_MOD_CACHE_DIRNAME,
    download_to_cache_getter=lambda: download_to_cache,
    resolve_direct_url_entry_getter=lambda: resolve_direct_url_entry,
    resolve_moddb_entry_getter=lambda: resolve_moddb_entry,
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions.update(MOD_SUPPORT.command_functions)
ensure_mod_state = MOD_SUPPORT.ensure_mod_state
apply_configured_mods = MOD_SUPPORT.apply_configured_mods
cleanup_configured_mods = MOD_SUPPORT.cleanup_configured_mods
paper_mod_command = MOD_SUPPORT.command_functions["mod"]


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
    result = cust.configure(server, ask, port, dir, eula=eula, exe_name=exe_name)
    ensure_mod_state(server)
    return result


def install(server, *, eula=False):
    """Download or validate the configured PaperMC server jar."""

    install_downloaded_jar(server)
    cust.install(server, eula=eula)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)

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
    """Report PaperMC server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


