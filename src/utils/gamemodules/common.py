"""Reusable helpers for AlphaGSM game module hook implementations."""

from __future__ import annotations

import copy
import importlib
import inspect
import os

from server import ServerError
from server.settable_keys import KeyResolutionError, SettingSpec, resolve_requested_key
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec


STANDARD_UPDATE_VALIDATE_OPTION = OptSpec(
    "v",
    ["validate"],
    "Validate the server files after updating",
    "validate",
    None,
    True,
)
STANDARD_UPDATE_RESTART_OPTION = OptSpec(
    "r",
    ["restart"],
    "Restart the server after updating",
    "restart",
    None,
    True,
)
STANDARD_UPDATE_CMDSPEC = CmdSpec(
    options=(STANDARD_UPDATE_VALIDATE_OPTION, STANDARD_UPDATE_RESTART_OPTION)
)
STANDARD_RESTART_CMDSPEC = CmdSpec()
STANDARD_DOWNLOAD_URL_OPTION = OptSpec(
    "u",
    ["url"],
    "Download URL to use.",
    "url",
    "URL",
    str,
)
STANDARD_DOWNLOAD_NAME_OPTION = OptSpec(
    "N",
    ["download-name"],
    "Archive filename to cache.",
    "download_name",
    "NAME",
    str,
)
STANDARD_DOWNLOAD_SOURCE_OPTIONS = (
    STANDARD_DOWNLOAD_URL_OPTION,
    STANDARD_DOWNLOAD_NAME_OPTION,
)
STANDARD_VERSION_OPTION = OptSpec(
    "v",
    ["version"],
    "Version to download.",
    "version",
    "VERSION",
    str,
)
STANDARD_ARTIFACT_VERSION_OPTION = OptSpec(
    "v",
    ["version"],
    "Artifact version to download.",
    "version",
    "VERSION",
    str,
)
STANDARD_EXE_NAME_SETTING = SettingSpec(
    canonical_key="exe_name",
    description="Server executable filename.",
)
STANDARD_DIR_SETTING = SettingSpec(
    canonical_key="dir",
    description="Install directory for the server.",
)
STANDARD_DOWNLOAD_URL_SETTING = SettingSpec(
    canonical_key="url",
    description="Download URL for the server archive.",
)
STANDARD_DOWNLOAD_NAME_SETTING = SettingSpec(
    canonical_key="download_name",
    description="Cached archive filename.",
)
STANDARD_VERSION_SETTING = SettingSpec(
    canonical_key="version",
    description="Requested upstream release version.",
)


def set_server_defaults(server, defaults):
    """Apply default datastore values without overwriting user state."""

    for key, value in defaults.items():
        if key not in server.data:
            server.data[key] = copy.deepcopy(value)


def set_steam_install_metadata(server, *, steam_app_id, steam_anonymous_login_possible):
    """Persist the standard Steam install metadata for a module."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible


def ensure_backup_config(server, *, backupfiles=None, targets, profile_name="default"):
    """Populate standard backup datastore keys when missing."""

    if backupfiles is not None:
        server.data.setdefault("backupfiles", list(backupfiles))
    ensure_backup_defaults(server, targets=targets, profile_name=profile_name)


def configure_port(server, ask, port, *, default_port, prompt):
    """Resolve and persist the server's main port value."""

    if port is None:
        port = server.data.get("port", default_port)
    if ask:
        inp = input("%s [%s] " % (prompt, port)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    return server.data["port"]


def configure_install_dir(server, ask, dir, *, prompt):
    """Resolve and persist the install directory with AlphaGSM's trailing slash style."""

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
    if ask:
        inp = input("%s [%s] " % (prompt, dir)).strip()
        if inp:
            dir = inp
    server.data["dir"] = os.path.join(dir, "")
    return server.data["dir"]


def configure_executable(server, *, exe_name):
    """Resolve and persist the executable filename/path."""

    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    return server.data["exe_name"]


def configure_download_source(
    server,
    ask,
    *,
    url=None,
    download_name=None,
    default_url=None,
    default_name=None,
    prompt,
    url_key="url",
    download_name_key="download_name",
):
    """Resolve standard archive download URL and cached filename settings."""

    if url is not None:
        server.data[url_key] = url
    elif url_key not in server.data and default_url is not None:
        server.data[url_key] = default_url
    if ask and url is None and server.data.get(url_key):
        inp = input("%s [%s] " % (prompt, server.data[url_key])).strip()
        if inp:
            server.data[url_key] = inp
    if download_name is not None:
        server.data[download_name_key] = download_name
    elif download_name_key not in server.data:
        server.data[download_name_key] = (
            os.path.basename(server.data.get(url_key, "")) or default_name
        )
    return server.data.get(url_key), server.data.get(download_name_key)


def configure_resolved_download_source(
    server,
    ask,
    *,
    version=None,
    url=None,
    download_name=None,
    resolve_download,
    prompt,
    default_name=None,
    version_key="version",
    url_key="url",
    download_name_key="download_name",
):
    """Resolve a versioned archive source, allow an override prompt, and persist the cache name."""

    if url is not None:
        server.data[url_key] = url
    elif server.data.get(url_key) in (None, ""):
        resolved_version, resolved_url = resolve_download(version=version or server.data.get(version_key))
        server.data[version_key] = resolved_version
        server.data[url_key] = resolved_url
    elif version is not None:
        server.data[version_key] = str(version)

    if ask and url is None and server.data.get(url_key):
        inp = input("%s [%s] " % (prompt, server.data[url_key])).strip()
        if inp:
            server.data[url_key] = inp

    if download_name is not None:
        server.data[download_name_key] = download_name
    elif server.data.get(download_name_key) in (None, ""):
        server.data[download_name_key] = (
            os.path.basename(server.data.get(url_key, "")) or default_name
        )
    return server.data.get(url_key), server.data.get(download_name_key)


def finalize_configure(server):
    """Persist datastore changes and return the standard configure result."""

    server.data.save()
    return (), {}


def _backup_module():
    return importlib.import_module("utils.backups.backups")


def _caller_backup_module():
    frame = inspect.currentframe()
    try:
        caller = frame.f_back
        if caller is not None:
            for name in ("backup_utils", "backups"):
                candidate = caller.f_globals.get(name)
                if candidate is not None:
                    return candidate
    finally:
        del frame
    return _backup_module()


def _runtime_module():
    return importlib.import_module("server.runtime")


def _proton_module():
    return importlib.import_module("utils.proton")


def _screen_module():
    return importlib.import_module("screen")


def _server_runtime_module():
    return importlib.import_module("server.runtime")


def ensure_backup_defaults(server, *, targets, profile_name="default"):
    """Ensure *server* has a minimal shared backup configuration."""

    if "backup" not in server.data:
        server.data["backup"] = {}
    server.data["backup"].setdefault("profiles", {})
    if not server.data["backup"]["profiles"]:
        server.data["backup"]["profiles"][profile_name] = {
            "targets": list(targets),
        }
    server.data["backup"].setdefault("schedule", [])
    if not server.data["backup"]["schedule"]:
        chosen_profile = profile_name
        if chosen_profile not in server.data["backup"]["profiles"]:
            chosen_profile = next(iter(server.data["backup"]["profiles"]))
        server.data["backup"]["schedule"].append((chosen_profile, 0, "days"))


def run_backup(server, profile=None, *, backup_module=None):
    """Run the standard AlphaGSM backup flow for *server*."""

    if backup_module is None:
        backup_module = _caller_backup_module()
    backup_module.backup(server.data["dir"], server.data["backup"], profile)


def sync_if_install_present(server, sync_server_config):
    """Run config sync only when the install root currently exists."""

    install_dir = server.data.get("dir")
    if not install_dir or not os.path.isdir(install_dir):
        return False
    sync_server_config(server)
    return True


def make_restart_hook():
    """Return a basic ``restart`` hook that stops then starts the server."""

    def restart(server):
        server.stop()
        server.start()

    restart.__name__ = "restart"
    return restart


def make_noop_status_hook():
    """Return a ``status`` hook with no extra output."""

    def status(server, verbose):
        return None

    status.__name__ = "status"
    return status


def print_unsupported_message(message="This server doesn't support generic messages yet"):
    """Print the standard explanation for unsupported generic messages."""

    print(message)


def make_server_message_hook(*, command="say", runtime_module=None):
    """Return a runtime-aware ``message`` hook using the given console command."""

    def message(server, msg):
        resolved_runtime_module = runtime_module or _server_runtime_module()
        resolved_runtime_module.send_to_server(server, "\n%s %s\n" % (command, msg))

    message.__name__ = "message"
    return message


def make_screen_message_hook(*, command="say"):
    """Backward-compatible alias for ``make_server_message_hook``."""

    return make_server_message_hook(command=command)


def build_setup_command_args(port_description, dir_description, *, setup_options=(), extra_optionalarguments=()):
    """Return the standard ``setup`` command args for modules with port/dir inputs."""

    return {
        "setup": CmdSpec(
            optionalarguments=(
                ArgSpec("PORT", port_description, int),
                ArgSpec("DIR", dir_description, str),
                *extra_optionalarguments,
            ),
            options=tuple(setup_options),
        )
    }


def build_setup_dir_command_args(dir_description, *, setup_options=(), extra_optionalarguments=()):
    """Return the standard ``setup`` command args for modules that only take ``DIR``."""

    return {
        "setup": CmdSpec(
            optionalarguments=(
                ArgSpec("DIR", dir_description, str),
                *extra_optionalarguments,
            ),
            options=tuple(setup_options),
        )
    }


def build_setup_update_restart_command_args(
    port_description,
    dir_description,
    *,
    setup_options=(),
    extra_optionalarguments=(),
):
    """Return standard ``setup``/``update``/``restart`` command args."""

    return {
        **build_setup_command_args(
            port_description,
            dir_description,
            setup_options=setup_options,
            extra_optionalarguments=extra_optionalarguments,
        ),
        **build_update_restart_command_args(),
    }


def build_setup_dir_update_restart_command_args(
    dir_description,
    *,
    setup_options=(),
    extra_optionalarguments=(),
):
    """Return standard ``setup``/``update``/``restart`` args for dir-only modules."""

    return {
        **build_setup_dir_command_args(
            dir_description,
            setup_options=setup_options,
            extra_optionalarguments=extra_optionalarguments,
        ),
        **build_update_restart_command_args(),
    }


def build_setup_download_command_args(
    port_description,
    dir_description,
    *,
    setup_options=(),
    extra_optionalarguments=(),
):
    """Return standard ``setup`` args for modules with archive URL/name options."""

    return build_setup_command_args(
        port_description,
        dir_description,
        setup_options=tuple(setup_options) + STANDARD_DOWNLOAD_SOURCE_OPTIONS,
        extra_optionalarguments=extra_optionalarguments,
    )


def build_setup_version_url_command_args(
    port_description,
    dir_description,
    *,
    version_option=STANDARD_VERSION_OPTION,
    url_option=STANDARD_DOWNLOAD_URL_OPTION,
    setup_options=(),
    extra_optionalarguments=(),
):
    """Return standard ``setup`` args for modules with version and direct URL options."""

    return build_setup_command_args(
        port_description,
        dir_description,
        setup_options=(version_option, url_option) + tuple(setup_options),
        extra_optionalarguments=extra_optionalarguments,
    )


def build_setup_version_download_command_args(
    port_description,
    dir_description,
    *,
    version_option=STANDARD_VERSION_OPTION,
    setup_options=(),
    extra_optionalarguments=(),
):
    """Return standard ``setup`` args for modules with versioned archive downloads."""

    return build_setup_command_args(
        port_description,
        dir_description,
        setup_options=(version_option,) + tuple(setup_options) + STANDARD_DOWNLOAD_SOURCE_OPTIONS,
        extra_optionalarguments=extra_optionalarguments,
    )


def build_update_restart_command_args():
    """Return the standard ``update`` and ``restart`` command specs."""

    return {
        "update": STANDARD_UPDATE_CMDSPEC,
        "restart": STANDARD_RESTART_CMDSPEC,
    }


def build_update_restart_command_descriptions(update_description, restart_description):
    """Return standard command descriptions for ``update`` and ``restart``."""

    return {
        "update": update_description,
        "restart": restart_description,
    }


def build_executable_path_setting_schema():
    """Return shared ``exe_name`` and ``dir`` SettingSpec entries."""

    return {
        "exe_name": STANDARD_EXE_NAME_SETTING,
        "dir": STANDARD_DIR_SETTING,
    }


def build_download_source_setting_schema():
    """Return shared ``url`` and ``download_name`` SettingSpec entries."""

    return {
        "url": STANDARD_DOWNLOAD_URL_SETTING,
        "download_name": STANDARD_DOWNLOAD_NAME_SETTING,
    }


def build_versioned_download_setting_schema():
    """Return shared ``url``/``download_name``/``version`` SettingSpec entries."""

    return {
        **build_download_source_setting_schema(),
        "version": STANDARD_VERSION_SETTING,
    }


def make_steamcmd_install_hook(
    *,
    steamcmd_module,
    steam_app_id,
    steam_anonymous_login_possible,
    sync_server_config=None,
    validate=False,
    post_download_hook=None,
    download_kwargs=None,
):
    """Return a standard SteamCMD-backed ``install`` hook."""

    def install(server):
        resolved_download_kwargs = _resolve_optional_mapping(download_kwargs, server) or {}
        os.makedirs(server.data["dir"], exist_ok=True)
        steamcmd_module.download(
            server.data["dir"],
            steam_app_id,
            steam_anonymous_login_possible,
            validate=validate,
            **resolved_download_kwargs,
        )
        if sync_server_config is not None:
            sync_if_install_present(server, sync_server_config)
        if post_download_hook is not None:
            post_download_hook(server)

    install.__name__ = "install"
    return install


def make_steamcmd_update_hook(
    *,
    steamcmd_module,
    steam_app_id,
    steam_anonymous_login_possible,
    sync_server_config=None,
    post_download_hook=None,
    download_kwargs=None,
):
    """Return a standard SteamCMD-backed ``update`` hook."""

    def update(server, validate=False, restart=False):
        try:
            server.stop()
        except Exception:
            print("Server has probably already stopped, updating")
        resolved_download_kwargs = _resolve_optional_mapping(download_kwargs, server) or {}
        steamcmd_module.download(
            server.data["dir"],
            steam_app_id,
            steam_anonymous_login_possible,
            validate=validate,
            **resolved_download_kwargs,
        )
        if sync_server_config is not None:
            sync_if_install_present(server, sync_server_config)
        if post_download_hook is not None:
            post_download_hook(server)
        print("Server up to date")
        if restart:
            print("Starting the server up")
            server.start()

    update.__name__ = "update"
    return update


def handle_basic_checkvalue(
    server,
    key,
    *value,
    int_keys=(),
    str_keys=(),
    custom_handlers=None,
    backup_module=None,
):
    """Validate common datastore edits used by many game modules."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        if backup_module is None:
            backup_module = _caller_backup_module()
        return backup_module.checkdatavalue(server.data["backup"], key[1:], *value)
    if len(value) == 0:
        raise ServerError("No value specified")

    key_name = key[0]
    handler = (custom_handlers or {}).get(key_name)
    if handler is not None:
        return handler(server, *value)
    if key_name in int_keys:
        return int(value[0])
    if key_name in str_keys:
        return str(value[0])
    raise ServerError("Unsupported key")


def make_basic_checkvalue(*, int_keys=(), str_keys=(), custom_handlers=None):
    """Return a ``checkvalue`` hook for simple typed datastore validation."""

    def checkvalue(server, key, *value):
        return handle_basic_checkvalue(
            server,
            key,
            *value,
            int_keys=int_keys,
            str_keys=str_keys,
            custom_handlers=custom_handlers,
        )

    checkvalue.__name__ = "checkvalue"
    return checkvalue


def handle_setting_schema_checkvalue(
    server,
    key,
    *value,
    setting_schema,
    resolved_int_keys=(),
    resolved_str_keys=(),
    raw_int_keys=(),
    raw_str_keys=(),
    resolved_handlers=None,
    raw_handlers=None,
    backup_module=None,
):
    """Validate datastore edits using ``setting_schema`` aliases plus raw fallback keys."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        if backup_module is None:
            backup_module = _caller_backup_module()
        return backup_module.checkdatavalue(server.data["backup"], key[1:], *value)
    if len(value) == 0:
        raise ServerError("No value specified")

    key_name = key[0]
    resolved = None
    resolved_error = None
    try:
        resolved = resolve_requested_key(key_name, setting_schema)
    except KeyResolutionError as ex:
        resolved_error = ex

    if resolved is not None:
        canonical_key = resolved.canonical_key
        handler = (resolved_handlers or {}).get(canonical_key)
        if handler is not None:
            return handler(server, *value)
        if canonical_key in resolved_int_keys:
            return int(value[0])
        if canonical_key in resolved_str_keys:
            return str(value[0])

    handler = (raw_handlers or {}).get(key_name)
    if handler is not None:
        return handler(server, *value)
    if key_name in raw_int_keys:
        return int(value[0])
    if key_name in raw_str_keys:
        return str(value[0])
    if resolved_error is not None:
        raise ServerError("Unsupported key") from resolved_error
    raise ServerError("Unsupported key")


def build_quake_setting_schema(
    *,
    include_fs_game=False,
    game_key="fs_game",
    game_aliases=(),
    game_description="The active game/mod directory.",
    fs_game_tokens=("+set", "fs_game"),
    port_tokens,
    hostname_tokens,
    map_tokens=("+map",),
    port_native_config_key=None,
    hostname_native_config_key=None,
    include_bind_address=False,
    bind_address_storage_key="bindaddress",
    bind_address_tokens=("+set", "net_ip"),
    hostname_before_port=False,
):
    """Build shared SettingSpec entries for Quake-family launch patterns."""

    schema = {}
    ordered_keys = []
    if include_fs_game:
        ordered_keys.append("fs_game")
    if hostname_before_port:
        ordered_keys.append("hostname")
        if include_bind_address:
            ordered_keys.append("bindaddress")
        ordered_keys.append("port")
    else:
        ordered_keys.append("port")
        ordered_keys.append("hostname")
        if include_bind_address:
            ordered_keys.append("bindaddress")
    ordered_keys.append("startmap")

    for key_name in ordered_keys:
        if key_name == "fs_game":
            schema[key_name] = SettingSpec(
                canonical_key=game_key,
                aliases=tuple(game_aliases),
                description=game_description,
                apply_to=("datastore", "launch_args"),
                launch_arg_tokens=fs_game_tokens,
                examples=("baseq3",),
            )
        elif key_name == "port":
            apply_to = ["datastore", "launch_args"]
            if port_native_config_key is not None:
                apply_to.append("native_config")
            schema[key_name] = SettingSpec(
                canonical_key="port",
                description="The game port for the server.",
                value_type="integer",
                apply_to=tuple(apply_to),
                native_config_key=port_native_config_key,
                launch_arg_tokens=port_tokens,
                examples=("27960",),
            )
        elif key_name == "hostname":
            apply_to = ["datastore", "launch_args"]
            if hostname_native_config_key is not None:
                apply_to.append("native_config")
            schema[key_name] = SettingSpec(
                canonical_key="hostname",
                description="The advertised server name.",
                apply_to=tuple(apply_to),
                native_config_key=hostname_native_config_key,
                launch_arg_tokens=hostname_tokens,
                examples=("AlphaGSM Arena",),
            )
        elif key_name == "bindaddress":
            schema[key_name] = SettingSpec(
                canonical_key="bindaddress",
                aliases=("bind_address",),
                description="The hosted IP address to bind for launch.",
                apply_to=("launch_args",),
                storage_key=bind_address_storage_key,
                launch_arg_tokens=bind_address_tokens,
                examples=("0.0.0.0",),
            )
        elif key_name == "startmap":
            schema[key_name] = SettingSpec(
                canonical_key="startmap",
                aliases=("map",),
                description="The startup map.",
                apply_to=("datastore", "launch_args"),
                launch_arg_tokens=map_tokens,
                examples=("q3dm17",),
            )

    return schema


def build_unreal_setting_schema(
    *,
    positional_key=None,
    positional_aliases=(),
    positional_description="The startup world or map.",
    include_maxplayers=False,
    include_servername=False,
    port_format="-Port={value}",
    queryport_format="-QueryPort={value}",
    maxplayers_format="-MaxPlayers={value}",
    servername_format="-ServerName={value}",
):
    """Build shared SettingSpec entries for Unreal-style launch patterns."""

    schema = {}

    if positional_key is not None:
        schema[positional_key] = SettingSpec(
            canonical_key=positional_key,
            aliases=tuple(positional_aliases),
            description=positional_description,
            apply_to=("datastore", "launch_args"),
            launch_arg_format="{value}",
        )

    schema["port"] = SettingSpec(
        canonical_key="port",
        description="The game port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format=port_format,
        examples=("7777",),
    )
    schema["queryport"] = SettingSpec(
        canonical_key="queryport",
        description="The query port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format=queryport_format,
        examples=("27015",),
    )

    if include_maxplayers:
        schema["maxplayers"] = SettingSpec(
            canonical_key="maxplayers",
            description="The maximum number of players.",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_format=maxplayers_format,
            examples=("16",),
        )

    if include_servername:
        schema["servername"] = SettingSpec(
            canonical_key="servername",
            description="The advertised server name.",
            apply_to=("datastore", "launch_args"),
            launch_arg_format=servername_format,
            examples=("AlphaGSM Server",),
        )

    return schema


def build_unreal_travel_arg(
    base_path,
    *,
    options=(),
    optional_options=(),
    flags=(),
):
    """Build a UE-style travel/map argument with ordered query-style segments."""

    arg = str(base_path)

    for key, value in options:
        arg += "?{}={}".format(key, value)

    for key, value in optional_options:
        if value not in (None, ""):
            arg += "?{}={}".format(key, value)

    for flag in flags:
        arg += "?{}".format(flag)

    return arg


def _resolve_optional_mapping(value, server):
    if callable(value):
        value = value(server)
    if value is None:
        return None
    return dict(value)


def make_runtime_requirements_builder(
    *,
    family,
    port_definitions=(),
    env=None,
    mounts=None,
    extra=None,
):
    """Return a ``get_runtime_requirements`` hook backed by shared builders."""

    def get_runtime_requirements(server):
        return _runtime_module().build_runtime_requirements(
            server,
            family=family,
            port_definitions=port_definitions,
            env=_resolve_optional_mapping(env, server),
            mounts=_resolve_optional_mapping(mounts, server),
            extra=_resolve_optional_mapping(extra, server),
        )

    get_runtime_requirements.__name__ = "get_runtime_requirements"
    return get_runtime_requirements


def make_container_spec_builder(
    *,
    family,
    get_start_command,
    port_definitions=(),
    env=None,
    mounts=None,
    stdin_open=True,
    tty=False,
    working_dir=None,
    extra=None,
):
    """Return a ``get_container_spec`` hook backed by shared builders."""

    def get_container_spec(server):
        return _runtime_module().build_container_spec(
            server,
            family=family,
            get_start_command=get_start_command,
            port_definitions=port_definitions,
            env=_resolve_optional_mapping(env, server),
            mounts=_resolve_optional_mapping(mounts, server),
            stdin_open=stdin_open,
            tty=tty,
            working_dir=working_dir,
            extra=_resolve_optional_mapping(extra, server),
        )

    get_container_spec.__name__ = "get_container_spec"
    return get_container_spec


def make_proton_runtime_requirements_builder(
    *,
    port_definitions=(),
    prefer_proton=False,
    extra_env=None,
):
    """Return a Proton-backed ``get_runtime_requirements`` hook."""

    def get_runtime_requirements(server):
        return _proton_module().get_runtime_requirements(
            server,
            port_definitions=port_definitions,
            prefer_proton=prefer_proton,
            extra_env=_resolve_optional_mapping(extra_env, server),
        )

    get_runtime_requirements.__name__ = "get_runtime_requirements"
    return get_runtime_requirements


def make_proton_container_spec_builder(
    *,
    get_start_command,
    port_definitions=(),
    prefer_proton=False,
    extra_env=None,
    working_dir=None,
):
    """Return a Proton-backed ``get_container_spec`` hook."""

    def get_container_spec(server):
        resolved_working_dir = working_dir
        if resolved_working_dir is None:
            resolved_working_dir = _proton_module().CONTAINER_SERVER_DIR
        return _proton_module().get_container_spec(
            server,
            get_start_command,
            port_definitions=port_definitions,
            prefer_proton=prefer_proton,
            extra_env=_resolve_optional_mapping(extra_env, server),
            working_dir=resolved_working_dir,
        )

    get_container_spec.__name__ = "get_container_spec"
    return get_container_spec