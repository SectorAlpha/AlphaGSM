"""SteamCMD installation and game-download helpers used by Steam game modules."""

import os
import os.path
from pathlib import Path
import re
import subprocess as sp
import time

from downloadermodules.url import download as url_download
from utils.settings import settings
from utils.platform_info import PLATFORM
from server.modsupport.workshop import normalize_workshop_identifier
from server.modsupport.errors import ModSupportError

# SteamCMD prefers an existing Steam directory, but an explicit configuration
# must always win regardless of whether that default directory exists.
_CONFIGURED_STEAMCMD_DIR = settings.user.getsection("downloader").getsection("steamcmd").get(
    "steamcmd_path"
)
_LINUX_STEAM_CANDIDATES = (
    "~/.local/share/Steam",
    "~/.steam/root",
    "~/.steam/steam",
)
_MAC_STEAM_CANDIDATE = "~/Library/Application Support/Steam"
_STEAM_FALLBACK = "~/Steam"


def _windows_registry_steam_dir():
    """Return the Steam client directory recorded in the Windows registry."""

    if os.name != "nt":
        return None
    import winreg  # pylint: disable=import-outside-toplevel

    queries = (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    )
    for hive, subkey, value_name in queries:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _kind = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        if value:
            return os.path.normpath(str(value))
    return None


def _steam_dir_candidates(platform):
    """Return Steam client directories to probe for *platform*, in order."""

    if platform == "windows":
        candidates = []
        registry = _windows_registry_steam_dir()
        if registry:
            candidates.append(registry)
        seen = {os.path.normcase(os.path.normpath(path)) for path in candidates}
        for key in ("ProgramFiles(x86)", "ProgramFiles"):
            root = os.environ.get(key)
            if not root:
                continue
            candidate = os.path.join(root, "Steam")
            marker = os.path.normcase(os.path.normpath(candidate))
            if marker in seen:
                continue
            seen.add(marker)
            candidates.append(candidate)
        return candidates
    if platform == "macos":
        return [_MAC_STEAM_CANDIDATE]
    return list(_LINUX_STEAM_CANDIDATES)


def _directory_with_separator(path):
    """Return *path* expanded and ending in a path separator."""

    expanded = os.path.expanduser(path)
    if expanded.endswith(("/", "\\")):
        return expanded
    return os.path.join(expanded, "")


def default_steamcmd_dir(platform=None):
    """Return the Steam directory for SteamCMD on this operating system.

    An existing client directory wins. Linux checks ``~/.local/share/Steam``,
    ``~/.steam/root``, and ``~/.steam/steam``. macOS checks
    ``~/Library/Application Support/Steam``. Windows checks the Steam
    registry path, then Program Files (x86) and Program Files. The fallback
    is ``~/Steam``, except on macOS, where the Library path is the fallback.
    """

    selected = platform or PLATFORM
    for candidate in _steam_dir_candidates(selected):
        expanded = os.path.expanduser(candidate)
        if os.path.isdir(expanded):
            return _directory_with_separator(expanded)
    if selected == "macos":
        return _directory_with_separator(_MAC_STEAM_CANDIDATE)
    return _directory_with_separator(_STEAM_FALLBACK)


def resolve_steamcmd_dir(configured=None, platform=None):
    """Return ``steamcmd_path`` when set, otherwise the detected directory."""

    if configured:
        return os.path.expanduser(str(configured))
    return default_steamcmd_dir(platform)


def steamcmd_executable_name(platform=None):
    """Return ``steamcmd.exe`` on Windows and ``steamcmd.sh`` elsewhere."""

    if (platform or PLATFORM) == "windows":
        return "steamcmd.exe"
    return "steamcmd.sh"


STEAMCMD_DIR = resolve_steamcmd_dir(_CONFIGURED_STEAMCMD_DIR)
STEAMCMD_EXE = os.path.join(STEAMCMD_DIR, steamcmd_executable_name())
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
STEAMCMD_SCRIPTS = os.path.expanduser(
    settings.user.getsection("steamcmd").get(
        "steamcmd_scripts",
        os.path.join(
            settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm"),
            "steamcmd_scripts",
        ),
    )
)
STEAMCMD_GAMEUPDATE_TEMPLATE = "steamcmd_gamescript_template.txt"
STEAMCMD_RETRIES = 3
STEAMCMD_RETRY_DELAY_SECONDS = 2
STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS = 5
_KNOWN_BARE_STATE_202_FLAKE_APP_IDS = frozenset(
    {"232130", "294420", "346680", "418480", "746200"}
)
# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit


def _normalise_install_path(path):
    """Return an absolute, user-expanded install path for SteamCMD commands."""
    return os.path.abspath(os.path.expanduser(path))


def _steamcmd_succeeded(output, app_id):
    """Return whether SteamCMD output includes a success marker for the app."""
    success_markers = (
        "Success! App '{}' fully installed.".format(app_id),
        "Success! App '{}' already up to date.".format(app_id),
    )
    return any(marker in output for marker in success_markers)


def _steamcmd_missing_manifest_flake(output, app_id):
    """Return whether SteamCMD reported the known missing-manifest flake."""

    if app_id in (None, ""):
        return False

    app_id = str(app_id)
    missing_config = "ERROR! Failed to install app '{}' (Missing configuration)".format(app_id)
    state_202 = "Error! App '{}' state is 0x202 after update job.".format(app_id)
    return missing_config in output and state_202 in output


def _steamcmd_state_202_flake(output, app_id):
    """Return whether SteamCMD reported a known transient state 0x202 flake."""

    if app_id in (None, ""):
        return False

    app_id = str(app_id)
    state_202 = "Error! App '{}' state is 0x202 after update job.".format(app_id)
    if state_202 not in output:
        return False

    return _steamcmd_missing_manifest_flake(output, app_id) or app_id in _KNOWN_BARE_STATE_202_FLAKE_APP_IDS


def _steamcmd_retry_delay(output, app_id):
    """Return the retry delay for known transient SteamCMD states."""

    if _steamcmd_state_202_flake(output, app_id):
        return STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS
    return STEAMCMD_RETRY_DELAY_SECONDS


def _get_login_args(steam_anonymous_login_possible):
    """Return the SteamCMD login arguments for anonymous or owned-game installs."""

    if steam_anonymous_login_possible:
        return ["+login", "anonymous"]
    username = settings.user.getsection("downloader").getsection("steamcmd").get("username")
    password = settings.user.getsection("downloader").getsection("steamcmd").get("password", "")
    if not username:
        raise RuntimeError(
            "SteamCMD username required for this server. Set [downloader.steamcmd] username in alphagsm.conf"
        )
    return ["+login", str(username), str(password)]


def _ensure_steamclient_symlinks():
    """Create ~/.steam/sdk{32,64}/steamclient.so symlinks expected by many
    dedicated server binaries.

    Many Steamworks-SDK game servers look for steamclient.so in the well-known
    paths ``~/.steam/sdk64/steamclient.so`` (64-bit) and
    ``~/.steam/sdk32/steamclient.so`` (32-bit).  SteamCMD standalone creates
    these files inside its own runtime directory but does *not* automatically
    create the ~/.steam/sdk* symlinks that the full Steam client would create.
    We create them here so that game servers relying on them start correctly.
    """
    home = os.path.expanduser("~")
    for bits in ("32", "64"):
        src = os.path.join(STEAMCMD_DIR, f"linux{bits}", "steamclient.so")
        if not os.path.isfile(src):
            continue
        dst_dir = os.path.join(home, ".steam", f"sdk{bits}")
        dst = os.path.join(dst_dir, "steamclient.so")
        if os.path.lexists(dst):
            continue
        os.makedirs(dst_dir, exist_ok=True)
        try:
            os.symlink(src, dst)
        except FileExistsError:
            continue


def install_steamcmd():
    """Ensure the SteamCMD runtime exists in the configured installation path."""

    if PLATFORM != "linux":
        raise RuntimeError(
            "This AlphaGSM installer uses the Linux SteamCMD client. Run AlphaGSM "
            "in a Linux environment or the manager container; selecting a Docker "
            "game runtime does not move installation off the host."
        )
    # if steamcmd dir does not exist, download it
    if not os.path.exists(STEAMCMD_DIR):
        os.makedirs(STEAMCMD_DIR)

    if not os.path.isfile(STEAMCMD_EXE):
        # if steamcmd files do not exist, download it
        url_download(STEAMCMD_DIR, (STEAMCMD_URL, "steamcmd_linux.tar.gz", "tar.gz"))


def download(
    path,
    Steam_AppID,
    steam_anonymous_login_possible,
    validate=True,
    mod=None,
    force_windows=False,
    force_platform=None,
    beta_branch=None,
    beta_password=None,
    auth_profile=None,
):
    """Download a game server via SteamCMD, optionally setting a GoldSrc mod.

    Args:
        path: Installation directory for the server files.
        Steam_AppID: The Steam application ID to download.
        steam_anonymous_login_possible: Whether the app allows anonymous login.
        validate: If ``True`` pass ``validate`` to SteamCMD.
        mod: Optional GoldSrc mod name (used for app 90).
        force_windows: If ``True`` instruct SteamCMD to download the Windows
            depot rather than the native Linux one.  Required for Windows-only
            game servers that are launched via Wine or Proton on Linux.
        force_platform: Optional explicit platform override such as
            ``"linux"`` or ``"windows"``.
        beta_branch: Optional Steam branch name to install.
        beta_password: Optional branch password paired with ``beta_branch``.
        auth_profile: Explicit reusable isolated session; never falls back to anonymous.
    """
    if auth_profile is not None:
        _download_with_profile(
            path, Steam_AppID, auth_profile, validate=validate, mod=mod,
            force_windows=force_windows, force_platform=force_platform,
            beta_branch=beta_branch, beta_password=beta_password,
        )
        return
    # check to see if steamcmd exists
    install_steamcmd()
    path = _normalise_install_path(path)

    print("Running SteamCMD")
    proc_list = [STEAMCMD_EXE]
    if force_platform is not None:
        force_platform = str(force_platform).strip().lower() or None
    if force_windows:
        if force_platform not in (None, "windows"):
            raise ValueError("force_windows cannot be combined with non-windows force_platform")
        force_platform = "windows"
    if force_platform is not None:
        proc_list.extend(["+@sSteamCmdForcePlatformType", force_platform])
    proc_list.extend(["+force_install_dir", path])
    proc_list.extend(_get_login_args(steam_anonymous_login_possible))
    if beta_branch:
        proc_list.extend(["+app_update", str(Steam_AppID), "-beta", str(beta_branch)])
        if beta_password:
            proc_list.extend(["-betapassword", str(beta_password)])
        proc_list.append("+quit")
        if validate:
            proc_list.insert(-1, "validate")
        last_output = ""
        for attempt in range(STEAMCMD_RETRIES):
            proc = sp.run(
                proc_list, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False
            )
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
            last_output = proc.stdout
            if proc.returncode == 0 and _steamcmd_succeeded(proc.stdout, Steam_AppID):
                _ensure_steamclient_symlinks()
                return
            if attempt + 1 < STEAMCMD_RETRIES:
                retry_delay = _steamcmd_retry_delay(proc.stdout, Steam_AppID)
                print(
                    "SteamCMD did not complete install cleanly, retrying in %ss..."
                    % (retry_delay,)
                )
                time.sleep(retry_delay)
        raise sp.CalledProcessError(proc.returncode, proc_list, output=last_output)
    if mod is not None:
        proc_list.extend(["+app_set_config", "90", "mod", str(mod)])
    proc_list.extend(["+app_update", str(Steam_AppID), "+quit"])
    if validate:
        proc_list.insert(-1, "validate")
    last_output = ""
    for attempt in range(STEAMCMD_RETRIES):
        proc = sp.run(
            proc_list, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False
        )
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        last_output = proc.stdout
        if proc.returncode == 0 and _steamcmd_succeeded(proc.stdout, Steam_AppID):
            _ensure_steamclient_symlinks()
            return
        if attempt + 1 < STEAMCMD_RETRIES:
            retry_delay = _steamcmd_retry_delay(proc.stdout, Steam_AppID)
            print(
                "SteamCMD did not complete install cleanly, retrying in %ss..."
                % (retry_delay,)
            )
            time.sleep(retry_delay)
    raise sp.CalledProcessError(proc.returncode, proc_list, output=last_output)


def _download_with_profile(path, app_id, profile, **options):
    """Download with cached credentials and suppress potentially private output."""
    from utils import steam_auth  # pylint: disable=import-outside-toplevel
    if options.get("beta_password"):
        raise steam_auth.SteamAuthError("Branch passwords are not supported with SteamCMD session profiles")
    with steam_auth.download_session(profile) as (executable, username, env, lock_fd):
        platform = options.get("force_platform")
        if platform is not None:
            platform = str(platform).strip().lower() or None
        if options.get("force_windows"):
            if platform not in (None, "windows"):
                raise ValueError("force_windows cannot be combined with non-windows force_platform")
            platform = "windows"
        command = [str(executable), "+@ShutdownOnFailedCommand", "1",
                   "+@NoPromptForPassword", "1"]
        if platform:
            command.extend(["+@sSteamCmdForcePlatformType", platform])
        command.extend(["+force_install_dir", _normalise_install_path(path), "+login", username])
        if options.get("mod") is not None:
            command.extend(["+app_set_config", "90", "mod", str(options["mod"])])
        command.extend(["+app_update", str(app_id)])
        if options.get("beta_branch"):
            command.extend(["-beta", str(options["beta_branch"])])
        if options.get("validate"):
            command.append("validate")
        command.append("+quit")
        print("Running SteamCMD with a local auth profile")
        try:
            result = steam_auth.run_steamcmd(command, lock_fd=lock_fd, stdin=sp.DEVNULL, stdout=sp.PIPE,
                            stderr=sp.STDOUT, text=True, check=False,
                            cwd=str(executable.parent), env=env, umask=0o077)
        except (OSError, sp.SubprocessError):
            raise steam_auth.SteamAuthError("SteamCMD profile download failed; retry login or check entitlement") from None
        if result.returncode != 0 or not _steamcmd_succeeded(result.stdout or "", app_id):
            raise steam_auth.SteamAuthError("SteamCMD profile download failed; retry login or check entitlement")


def download_workshop_item(path, workshop_app_id, workshop_item_id, steam_anonymous_login_possible):
    """Download a Workshop item, requiring item-specific success and real content."""

    try:
        workshop_item_id = normalize_workshop_identifier(workshop_item_id)
    except ModSupportError as exc:
        raise ValueError(str(exc)) from exc
    ids = ((workshop_app_id, 32), (workshop_item_id, 64))
    for value, bits in ids:
        if not re.fullmatch(r"[0-9]{1,20}", str(value)) or not 0 < int(value) < 2**bits:
            raise ValueError("Steam Workshop app and item IDs must be positive numeric IDs")
    workshop_app_id, workshop_item_id = (str(int(value)) for value, _ in ids)

    install_steamcmd()
    path = _normalise_install_path(path)
    content_roots = [
        (Path(root) / "steamapps" / "workshop" / "content" / workshop_app_id / workshop_item_id).resolve()
        for root in (path, STEAMCMD_DIR)
    ]
    success_pattern = re.compile(
        rf'Success\. Downloaded item {workshop_item_id} to "([^"\r\n]+)"'
    )

    print("Running SteamCMD workshop download")
    proc_list = [STEAMCMD_EXE]
    proc_list.extend(["+force_install_dir", path])
    proc_list.extend(_get_login_args(steam_anonymous_login_possible))
    proc_list.extend(
        ["+workshop_download_item", str(workshop_app_id), str(workshop_item_id), "+quit"]
    )
    last_output = ""
    for attempt in range(STEAMCMD_RETRIES):
        proc = sp.run(
            proc_list, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False
        )
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        last_output = proc.stdout
        success = success_pattern.search(proc.stdout)
        if proc.returncode == 0 and success and "ERROR!" not in proc.stdout:
            reported_path = Path(success.group(1))
            content_dir = reported_path.resolve()
            # Legacy Workshop uploads report a payload filename instead of its directory.
            if (reported_path.is_file() and not reported_path.is_symlink()
                    and reported_path.stat().st_size > 0):
                content_dir = content_dir.parent
            if content_dir in content_roots and content_dir.is_dir() and any(
                file.is_file() and not file.is_symlink() and file.stat().st_size > 0
                for file in content_dir.rglob("*")
            ):
                return str(content_dir)
        if any(error in proc.stdout.lower() for error in ("access denied", "no subscription", "file not found")):
            last_output = (
                "Steam Workshop item is unavailable or this game does not permit anonymous downloads. "
                "An entitled Steam account may be required.\n" + proc.stdout
            )
            break
        if attempt + 1 < STEAMCMD_RETRIES:
            retry_delay = _steamcmd_retry_delay(proc.stdout, workshop_app_id)
            print(
                "SteamCMD did not complete workshop download cleanly, retrying in %ss..."
                % (retry_delay,)
            )
            time.sleep(retry_delay)
    raise sp.CalledProcessError(proc.returncode or 1, proc_list, output=last_output)


def get_autoupdate_script(name, path, app_id, force=False, mod=None):
    """
    Gets the autoupdate script
    If it does not exist, write it
    Write it anyway if force = True
    """
    if not os.path.isdir(STEAMCMD_SCRIPTS):
        os.mkdir(STEAMCMD_SCRIPTS)
    file_name = os.path.join(STEAMCMD_SCRIPTS, "") + name + "_update.txt"
    if not os.path.isfile(file_name) or force:
        path = _normalise_install_path(path)
        steamcmd_gameupdate_text = open(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), STEAMCMD_GAMEUPDATE_TEMPLATE
            ),
            "r",
        ).read()
        mod_line = ""
        if mod is not None:
            mod_line = "app_set_config 90 mod %s\n" % (mod,)
        steamcmd_gameupdate_text = steamcmd_gameupdate_text % (path, mod_line, app_id)
        f = open(file_name, "w")
        f.write(steamcmd_gameupdate_text)
        f.close()
    return file_name
