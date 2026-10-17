"""GRAV dedicated server lifecycle helpers using owned game files."""

import os
import subprocess as sp

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.gamemodules import common as gamemodule_common

# The developer ships the Win32 dedicated server inside owned Steam app 332500.
# Anonymous SteamCMD may mount no depot. A saved profile must not fall back.
STEAM_APP_ID = 332500
steam_app_id = STEAM_APP_ID
steam_anonymous_login_possible = True
DEFAULT_EXE_NAME = "CAGGameServer-Win32-Shipping"

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The game port to use for the GRAV server",
    "The directory containing the GRAV server files",
)
command_descriptions = {}
command_functions = {}
setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name=DEFAULT_EXE_NAME):
    """Collect and store configuration values for a GRAV server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "peerport": "7778",
            "queryport": "27015",
            "maxplayers": "32",
            "servername": server.name,
            "adminpassword": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["CAGGame", "Cloud"],
        targets=["CAGGame", "Cloud"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where are the GRAV server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _missing_server_tree(server):
    """Raise the owned-tree error without echoing a SteamCMD command line."""

    expected = os.path.basename(server.data.get("exe_name") or DEFAULT_EXE_NAME)
    gamemodule_common.raise_byo_requirement(
        "gravserver",
        "an owned GRAV dedicated server install",
        actions=(
            "Stage the Win32 GRAV tree so {} exists under <install_dir>".format(expected),
            "Retry setup once that dedicated server executable is present",
        ),
        docs_slug="gravserver",
    )


def _executable_names(server):
    """Return configured and Win32 shipping names, including the .exe form."""

    names = []
    configured = server.data.get("exe_name") or DEFAULT_EXE_NAME
    for name in (
        configured,
        DEFAULT_EXE_NAME,
        DEFAULT_EXE_NAME + ".exe",
        configured + ".exe" if not str(configured).endswith(".exe") else configured,
    ):
        if name and name not in names:
            names.append(name)
    return names


def _locate_executable(server):
    """Find the dedicated executable at the install root or nested under it."""

    for name in _executable_names(server):
        try:
            return gamemodule_common.resolve_install_executable(server, exe_name=name)
        except ServerError:
            continue
    return None


def _remember_executable(server, path):
    """Store the located executable relative to the install directory."""

    install_dir = os.path.abspath(server.data["dir"])
    relative = os.path.relpath(path, install_dir)
    if server.data.get("exe_name") != relative:
        server.data["exe_name"] = relative
        save = getattr(server.data, "save", None)
        if callable(save):
            save()
    return relative


def _download_kwargs(server):
    """Pass a saved auth profile only when one is set.

    Linux needs the Windows depot. No profile keeps the anonymous attempt.
    A saved profile never falls back to anonymous inside SteamCMD.
    """

    kwargs = {}
    if IS_LINUX:
        kwargs["force_windows"] = True
    profile = server.data.get("steam_auth_profile")
    if profile:
        kwargs["auth_profile"] = profile
    return kwargs


def _download_dedicated_server(server):
    """Install Steam app 332500 without surfacing a login command line."""

    try:
        steamcmd.download(
            server.data["dir"],
            STEAM_APP_ID,
            steam_anonymous_login_possible,
            **_download_kwargs(server),
        )
    except (OSError, RuntimeError, sp.SubprocessError) as exc:
        output = getattr(exc, "output", None) or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", "replace")
        message = "SteamCMD could not install GRAV app 332500"
        if "no subscription" in str(output).lower():
            message = "SteamCMD app 332500 did not mount a GRAV depot for this login"
        raise ServerError(message) from None


def install(server):
    """Download Steam app 332500 or accept an already staged Win32 server tree."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = _locate_executable(server)
    if exe_path is None:
        _download_dedicated_server(server)
        exe_path = _locate_executable(server)
    if exe_path is None:
        _missing_server_tree(server)
    _remember_executable(server, exe_path)


def _launcher_and_cwd(server, exe_path):
    """Match the owned Binaries worker, which starts Win32\\server from Binaries."""

    install_dir = os.path.abspath(server.data["dir"])
    relative = os.path.relpath(exe_path, install_dir)
    parts = relative.split(os.sep)
    if parts[-3:] == ["Binaries", "Win32", os.path.basename(exe_path)]:
        return ("./Win32/" + os.path.basename(exe_path), os.path.join(install_dir, "Binaries", ""))
    _exe_path, launcher, cwd = gamemodule_common.resolve_install_launcher(server)
    return launcher, cwd


def get_start_command(server):
    """Build the command used to launch a GRAV dedicated server."""

    exe_path = _locate_executable(server)
    if exe_path is None:
        _missing_server_tree(server)
    _remember_executable(server, exe_path)
    launcher, cwd = _launcher_and_cwd(server, exe_path)
    command = [
        launcher,
        "brokerstart?NumHomePlanets=1?AdminPassword=%s?PlanetManagerName=\"defaultmetaverse\"?PlanetPortOffset=0?steamsockets?Port=%s?PeerPort=%s?QueryPort=%s?MaxPlayers=%s?CloudDir=\"CharacterSaveData\"?SteamDontAdvertise=0?AllowPVP=1?DoBaseDecay=1?ServerName=%s"
        % (
            server.data["adminpassword"],
            server.data["port"],
            server.data["peerport"],
            server.data["queryport"],
            server.data["maxplayers"],
            server.data["servername"],
        ),
        "-seekfreeloadingserver",
        "-unattended",
    ]
    if IS_LINUX:
        wineprefix = server.data.get("wineprefix") or os.path.join(server.data["dir"], "wineprefix")
        command = proton.wrap_xvfb_command(
            command,
            wineprefix=wineprefix,
            prefer_proton=False,
        )
        command = proton.prepend_env_assignments(
            command,
            SteamAppId=str(STEAM_APP_ID),
            SteamGameId=str(STEAM_APP_ID),
            WINEDEBUG="-all",
        )
    return (command, cwd)


def get_query_address(server):
    """Return GRAV's Steam A2S endpoint on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop GRAV by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed GRAV status is not implemented yet."""


def message(server, msg):
    """GRAV has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a GRAV server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported GRAV datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "peerport", "queryport", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "adminpassword"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)


def get_asset_requirements(server):
    """Describe this game's owned files, acquisition routes and staging limits."""
    from utils.byo_files import load_requirements
    return load_requirements(server, __file__, 'byo_assets.json')
