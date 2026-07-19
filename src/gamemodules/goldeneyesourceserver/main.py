"""GoldenEye: Source dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

SOURCE_2007_APP_ID = 310
GES_RELEASE_VERSION = "5.0.6"
GES_RELEASE_SHA256 = (
    "79643189e9d6549e13ed9545d2277cb34bac05fff645d44d9de1f0ab030610d3"
)
PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
)
MAX_STAGED_SYMLINK_HOPS = 40

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The game port to use for the GoldenEye: Source server",
    "The directory to install GoldenEye: Source in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="srcds_run",
):
    """Collect and store configuration values for a GoldenEye: Source server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "game": "gesource",
            "maxplayers": "16",
            "startmap": "ge_archives",
            "source_app_id": SOURCE_2007_APP_ID,
            "artifact_version": GES_RELEASE_VERSION,
            "artifact_sha256": GES_RELEASE_SHA256,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["gesource", "gesource/cfg"],
        targets=["gesource", "gesource/cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the GoldenEye: Source server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def get_provider_requirements(server):
    """Declare the complete operator-staged tree required by this BYO module."""

    exe_name = server.data.get("exe_name", "srcds_run")
    return [
        {
            "provider": "operator",
            "kind": "asset",
            "keys": (),
            "required_for": ("setup", "start"),
            "support_category": "assets",
            "summary": (
                "a complete staged GoldenEye: Source dedicated server tree "
                "containing the Source 2007/AppID 310 base and preserved "
                "top-level gesource content"
            ),
            "actions": (
                "Install the Source SDK Base 2007 Dedicated Server (Steam AppID 310) into <install_dir>",
                "Copy the complete GoldenEye: Source 5.0.6 gesource directory to <install_dir>/gesource without an extra wrapper directory",
                (
                    "Write exactly 310 to <install_dir>/steam_appid.txt as a "
                    "required operator marker; this accidental mismatch guard "
                    "does not authenticate asset provenance"
                ),
                (
                    "Manually compare the GoldenEye 5.0.6 artifact SHA-256 "
                    "against {}; AlphaGSM does not verify the artifact"
                ).format(
                    GES_RELEASE_SHA256,
                ),
                "Ensure <install_dir>/{} is executable, then retry setup or start".format(
                    exe_name
                ),
            ),
            "docs_slug": "goldeneyesourceserver",
        }
    ]


def _path_is_contained(real_install_dir, path):
    try:
        return (
            os.path.commonpath((real_install_dir, os.path.abspath(path)))
            == real_install_dir
        )
    except ValueError:
        return False


def _staged_path_resolution_problem(install_dir, path):
    """Validate every path and relative symlink hop below the staged root."""

    real_install_dir = os.path.realpath(install_dir)
    pending = os.path.relpath(path, install_dir).split(os.sep)
    resolved = real_install_dir
    seen_states = set()
    symlink_hops = 0

    while pending:
        component = pending.pop(0)
        if component in ("", "."):
            continue
        if component == "..":
            parent = os.path.dirname(resolved)
            if not _path_is_contained(real_install_dir, parent):
                return (
                    "leaves the install root during symlink resolution and is "
                    "outside the install root"
                )
            resolved = parent
            continue

        candidate = os.path.join(resolved, component)
        if not _path_is_contained(real_install_dir, candidate):
            return (
                "leaves the install root during symlink resolution and is "
                "outside the install root"
            )
        if not os.path.islink(candidate):
            physical_candidate = os.path.realpath(candidate)
            if not _path_is_contained(real_install_dir, physical_candidate):
                return "resolves outside the install root"
            resolved = physical_candidate
            continue

        state = (candidate, tuple(pending))
        symlink_hops += 1
        if state in seen_states or symlink_hops > MAX_STAGED_SYMLINK_HOPS:
            return "contains a symlink cycle or an excessively long symlink chain"
        seen_states.add(state)

        try:
            target = os.readlink(candidate)
        except OSError as exc:
            return "could not inspect symlink {}: {}".format(candidate, exc)
        if os.path.isabs(target):
            return (
                "uses an absolute symlink; absolute symlinks are not portable "
                "to the Docker runtime"
            )
        pending = target.split(os.sep) + pending
        resolved = os.path.dirname(candidate)

    if not _path_is_contained(real_install_dir, os.path.realpath(resolved)):
        return "resolves outside the install root"
    return None


def _staged_tree_symlink_problem(install_dir):
    """Inspect every staged symlink without traversing symlinked directories."""

    pending_directories = [install_dir]
    while pending_directories:
        current_dir = pending_directories.pop()
        relative_dir = os.path.relpath(current_dir, install_dir)
        try:
            with os.scandir(current_dir) as scanned_entries:
                entries = sorted(scanned_entries, key=lambda entry: entry.name)
        except OSError:
            return "could not inspect staged tree directory {}".format(relative_dir)

        child_directories = []
        for entry in entries:
            relative_path = os.path.relpath(entry.path, install_dir)
            try:
                if entry.is_symlink():
                    problem = _staged_path_resolution_problem(
                        install_dir, entry.path
                    )
                    if problem:
                        return "staged symlink {} {}".format(relative_path, problem)
                    continue
                if entry.is_dir(follow_symlinks=False):
                    child_directories.append(entry.path)
            except OSError:
                return "could not inspect staged tree entry {}".format(relative_path)

        pending_directories.extend(reversed(child_directories))

    return None


def _staged_layout_problem(server):
    install_dir = os.path.abspath(server.data["dir"])
    exe_name = server.data["exe_name"]
    tree_problem = _staged_tree_symlink_problem(install_dir)
    if tree_problem:
        return tree_problem

    required_paths = (
        (exe_name, os.path.isfile),
        ("steam_appid.txt", os.path.isfile),
        ("bin", os.path.isdir),
        ("hl2", os.path.isdir),
        ("gesource/gameinfo.txt", os.path.isfile),
        ("gesource/maps/ge_archives.bsp", os.path.isfile),
    )
    missing = []
    for relative_path, predicate in required_paths:
        staged_path = os.path.join(install_dir, relative_path)
        resolution_problem = _staged_path_resolution_problem(install_dir, staged_path)
        if resolution_problem:
            return "required staged path {} {}".format(
                relative_path, resolution_problem
            )
        if not predicate(staged_path):
            missing.append(relative_path)

    if missing:
        return "missing required staged path(s): {}".format(", ".join(missing))

    app_id_path = os.path.join(install_dir, "steam_appid.txt")
    try:
        with open(app_id_path, "r", encoding="utf-8", newline="") as app_id_file:
            staged_app_id = app_id_file.read()
    except OSError as exc:
        return "could not read steam_appid.txt: {}".format(exc)
    app_id = str(SOURCE_2007_APP_ID)
    if staged_app_id not in (app_id, app_id + "\n", app_id + "\r\n"):
        return "steam_appid.txt must contain exactly {}".format(SOURCE_2007_APP_ID)

    if not os.access(os.path.join(install_dir, exe_name), os.X_OK):
        return "{} is present but is not executable".format(exe_name)
    return None


def _assert_complete_staged_tree(server):
    problem = _staged_layout_problem(server)
    if problem is None:
        return
    requirement = get_provider_requirements(server)[0]
    gamemodule_common.raise_byo_requirement(
        "goldeneyesourceserver",
        requirement["summary"],
        actions=tuple(requirement["actions"]) + ("Current staged layout: " + problem,),
        docs_slug=requirement["docs_slug"],
    )


def install(server):
    """Validate the complete GoldenEye: Source tree staged by the operator."""

    os.makedirs(server.data["dir"], exist_ok=True)
    _assert_complete_staged_tree(server)
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a GoldenEye: Source dedicated server."""

    _assert_complete_staged_tree(server)
    return (
        [
            "./" + server.data["exe_name"],
            "-game",
            server.data["game"],
            "+map",
            server.data["startmap"],
            "+maxplayers",
            str(server.data["maxplayers"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop GoldenEye: Source using the standard shell interrupt."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def message(server, msg):
    """GoldenEye: Source has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a GoldenEye: Source server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported GoldenEye: Source datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("exe_name", "dir", "game", "startmap"),
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=PORT_DEFINITIONS,
)

get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=PORT_DEFINITIONS,
    stdin_open=True,
)
