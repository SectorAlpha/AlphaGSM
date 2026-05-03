from types import SimpleNamespace

import pytest

from server import ServerError
from utils.gamemodules import common as gamemodule_common


class DummyData(dict):
    def save(self):
        self["_saved"] = True


def make_server(**data):
    return SimpleNamespace(name="demo", data=DummyData(data))


def test_ensure_backup_defaults_initializes_profile_and_schedule():
    server = make_server()

    gamemodule_common.ensure_backup_defaults(server, targets=("world", "config"))

    assert server.data["backup"]["profiles"]["default"]["targets"] == [
        "world",
        "config",
    ]
    assert server.data["backup"]["schedule"] == [("default", 0, "days")]


def test_ensure_backup_defaults_preserves_existing_backup_config():
    server = make_server(
        backup={
            "profiles": {"custom": {"targets": ["save"]}},
            "schedule": [("custom", 1, "days")],
        }
    )

    gamemodule_common.ensure_backup_defaults(server, targets=("world",))

    assert server.data["backup"]["profiles"] == {
        "custom": {"targets": ["save"]}
    }
    assert server.data["backup"]["schedule"] == [("custom", 1, "days")]


def test_handle_basic_checkvalue_supports_int_string_and_custom_keys():
    server = make_server(backup={})

    result = gamemodule_common.handle_basic_checkvalue(
        server,
        ("server_name",),
        "Alpha",
        int_keys=("port",),
        str_keys=("server_name",),
        custom_handlers={"slots": lambda _server, *value: str(int(value[0]))},
    )

    assert result == "Alpha"
    assert (
        gamemodule_common.handle_basic_checkvalue(
            server,
            ("port",),
            "27015",
            int_keys=("port",),
        )
        == 27015
    )
    assert (
        gamemodule_common.handle_basic_checkvalue(
            server,
            ("slots",),
            "24",
            custom_handlers={"slots": lambda _server, *value: str(int(value[0]))},
        )
        == "24"
    )


def test_handle_basic_checkvalue_delegates_backup_keys(monkeypatch):
    server = make_server(backup={"profiles": {}})
    seen = {}

    backup_module = SimpleNamespace()

    def fake_checkdatavalue(data, key, *value):
        seen["data"] = data
        seen["key"] = key
        seen["value"] = value
        return "ok"

    backup_module.checkdatavalue = fake_checkdatavalue
    monkeypatch.setattr(gamemodule_common, "_backup_module", lambda: backup_module)

    result = gamemodule_common.handle_basic_checkvalue(
        server,
        ("backup", "profiles", "default"),
        "world",
    )

    assert result == "ok"
    assert seen == {
        "data": {"profiles": {}},
        "key": ("profiles", "default"),
        "value": ("world",),
    }


def test_handle_setting_schema_checkvalue_supports_resolved_and_raw_keys():
    from server.settable_keys import SettingSpec

    server = make_server(backup={})
    schema = {
        "map": SettingSpec(canonical_key="map", aliases=("gamemap",), storage_key="levelname"),
        "maxplayers": SettingSpec(canonical_key="maxplayers"),
    }

    assert (
        gamemodule_common.handle_setting_schema_checkvalue(
            server,
            ("gamemap",),
            "world_two",
            setting_schema=schema,
            resolved_str_keys=("map",),
            raw_str_keys=("levelname",),
        )
        == "world_two"
    )
    assert (
        gamemodule_common.handle_setting_schema_checkvalue(
            server,
            ("maxplayers",),
            "24",
            setting_schema=schema,
            resolved_handlers={"maxplayers": lambda _server, *value: str(int(value[0]))},
        )
        == "24"
    )
    assert (
        gamemodule_common.handle_setting_schema_checkvalue(
            server,
            ("levelname",),
            "world_three",
            setting_schema=schema,
            raw_str_keys=("levelname",),
        )
        == "world_three"
    )


def test_handle_setting_schema_checkvalue_delegates_backup_keys(monkeypatch):
    server = make_server(backup={"profiles": {}})
    seen = {}
    backup_module = SimpleNamespace()

    def fake_checkdatavalue(data, key, *value):
        seen["data"] = data
        seen["key"] = key
        seen["value"] = value
        return "ok"

    backup_module.checkdatavalue = fake_checkdatavalue

    result = gamemodule_common.handle_setting_schema_checkvalue(
        server,
        ("backup", "profiles", "default"),
        "world",
        setting_schema={},
        backup_module=backup_module,
    )

    assert result == "ok"
    assert seen == {
        "data": {"profiles": {}},
        "key": ("profiles", "default"),
        "value": ("world",),
    }


def test_build_quake_setting_schema_preserves_order_and_metadata():
    schema = gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
        port_native_config_key="net_port",
        hostname_native_config_key="sv_hostname",
        include_bind_address=True,
        hostname_before_port=True,
    )

    assert list(schema) == ["fs_game", "hostname", "bindaddress", "port", "startmap"]
    assert schema["hostname"].native_config_key == "sv_hostname"
    assert schema["port"].native_config_key == "net_port"
    assert schema["bindaddress"].storage_key == "bindaddress"
    assert schema["bindaddress"].launch_arg_tokens == ("+set", "net_ip")
    assert schema["startmap"].aliases == ("map",)


def test_build_unreal_setting_schema_preserves_order_and_metadata():
    schema = gamemodule_common.build_unreal_setting_schema(
        positional_key="world",
        positional_aliases=("map",),
        include_maxplayers=True,
        include_servername=True,
    )

    assert list(schema) == ["world", "port", "queryport", "maxplayers", "servername"]
    assert schema["world"].aliases == ("map",)
    assert schema["world"].launch_arg_format == "{value}"
    assert schema["port"].launch_arg_format == "-Port={value}"
    assert schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert schema["maxplayers"].launch_arg_format == "-MaxPlayers={value}"
    assert schema["servername"].launch_arg_format == "-ServerName={value}"


def test_build_unreal_travel_arg_preserves_order_and_optional_values():
    arg = gamemodule_common.build_unreal_travel_arg(
        "/Game/Maps/TestWorld",
        options=(("SERVERNAME", '"AlphaGSM Demo"'), ("WORLDNAME", '"World"')),
        optional_options=(("PASSWORD", '"secret"'), ("IGNORED", "")),
        flags=("CROSSPLAY", "listen"),
    )

    assert arg == (
        '/Game/Maps/TestWorld?SERVERNAME="AlphaGSM Demo"?WORLDNAME="World"'
        '?PASSWORD="secret"?CROSSPLAY?listen'
    )


def test_build_update_restart_command_helpers_reuse_standard_specs():
    command_args = gamemodule_common.build_update_restart_command_args()
    descriptions = gamemodule_common.build_update_restart_command_descriptions(
        "Update demo server.",
        "Restart demo server.",
    )

    assert command_args["update"] is gamemodule_common.STANDARD_UPDATE_CMDSPEC
    assert command_args["restart"] is gamemodule_common.STANDARD_RESTART_CMDSPEC
    assert command_args["update"].options == (
        gamemodule_common.STANDARD_UPDATE_VALIDATE_OPTION,
        gamemodule_common.STANDARD_UPDATE_RESTART_OPTION,
    )
    assert descriptions == {
        "update": "Update demo server.",
        "restart": "Restart demo server.",
    }


def test_build_executable_path_setting_schema_reuses_standard_specs():
    schema = gamemodule_common.build_executable_path_setting_schema()

    assert schema == {
        "exe_name": gamemodule_common.STANDARD_EXE_NAME_SETTING,
        "dir": gamemodule_common.STANDARD_DIR_SETTING,
    }


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ((), (), "Invalid key"),
        (("port",), (), "No value specified"),
        (("unknown",), ("x",), "Unsupported key"),
    ],
)
def test_handle_basic_checkvalue_rejects_invalid_inputs(key, value, message):
    server = make_server(backup={})

    with pytest.raises(ServerError, match=message):
        gamemodule_common.handle_basic_checkvalue(
            server,
            key,
            *value,
            int_keys=("port",),
            str_keys=("name",),
        )


def test_make_runtime_requirements_builder_uses_shared_runtime_builder(tmp_path):
    server = make_server(dir=str(tmp_path), port=25565)
    builder = gamemodule_common.make_runtime_requirements_builder(
        family="java",
        port_definitions=(("port", "tcp"),),
        env=lambda current_server: {"ALPHAGSM_SERVER": current_server.name},
        extra=lambda _current_server: {"java": 21},
    )

    requirements = builder(server)

    assert requirements["family"] == "java"
    assert requirements["env"] == {"ALPHAGSM_SERVER": "demo"}
    assert requirements["java"] == 21
    assert requirements["ports"] == [{"host": 25565, "container": 25565, "protocol": "tcp"}]


def test_make_container_spec_builder_uses_shared_runtime_builder(tmp_path):
    server = make_server(dir=str(tmp_path), port=25565)

    def get_start_command(current_server):
        return (["java", "-jar", "server.jar"], current_server.data["dir"])

    builder = gamemodule_common.make_container_spec_builder(
        family="java",
        get_start_command=get_start_command,
        port_definitions=(("port", "tcp"),),
        env={"ALPHAGSM_SERVER_JAR": "server.jar"},
        tty=True,
    )

    spec = builder(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["tty"] is True
    assert spec["command"] == ["java", "-jar", "server.jar"]
    assert spec["env"] == {"ALPHAGSM_SERVER_JAR": "server.jar"}


def test_make_proton_builders_forward_arguments(monkeypatch):
    runtime_calls = []
    container_calls = []
    proton_module = SimpleNamespace(CONTAINER_SERVER_DIR="/srv/server")

    proton_module.get_runtime_requirements = (
        lambda server, **kwargs: runtime_calls.append((server, kwargs))
        or {"engine": "docker"}
    )
    proton_module.get_container_spec = (
        lambda server, get_start_command, **kwargs: container_calls.append(
            (server, get_start_command, kwargs)
        )
        or {"command": ["server.exe"]}
    )
    monkeypatch.setattr(gamemodule_common, "_proton_module", lambda: proton_module)

    server = make_server(port=7777)

    def get_start_command(current_server):
        return ([current_server.data.get("exe_name", "server.exe")], "/tmp")

    runtime_builder = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=(("port", "udp"),),
        prefer_proton=True,
        extra_env=lambda current_server: {"SERVER_NAME": current_server.name},
    )
    container_builder = gamemodule_common.make_proton_container_spec_builder(
        get_start_command=get_start_command,
        port_definitions=(("port", "udp"),),
        prefer_proton=True,
        extra_env={"SERVER_NAME": "demo"},
    )

    assert runtime_builder(server) == {"engine": "docker"}
    assert container_builder(server) == {"command": ["server.exe"]}
    assert runtime_calls == [
        (
            server,
            {
                "port_definitions": (("port", "udp"),),
                "prefer_proton": True,
                "extra_env": {"SERVER_NAME": "demo"},
            },
        )
    ]
    assert container_calls == [
        (
            server,
            get_start_command,
            {
                "port_definitions": (("port", "udp"),),
                "prefer_proton": True,
                "extra_env": {"SERVER_NAME": "demo"},
                "working_dir": "/srv/server",
            },
        )
    ]


def test_make_restart_hook_stops_then_starts_server():
    calls = []
    server = SimpleNamespace(
        stop=lambda: calls.append("stop"),
        start=lambda: calls.append("start"),
    )

    restart = gamemodule_common.make_restart_hook()

    restart(server)

    assert calls == ["stop", "start"]


def test_make_noop_status_hook_returns_none():
    status = gamemodule_common.make_noop_status_hook()

    assert status(SimpleNamespace(), 1) is None


def test_print_unsupported_message_uses_standard_notice(capsys):
    gamemodule_common.print_unsupported_message()

    assert capsys.readouterr().out == "This server doesn't support generic messages yet\n"


def test_print_unsupported_message_accepts_custom_notice(capsys):
    gamemodule_common.print_unsupported_message("Custom unsupported message")

    assert capsys.readouterr().out == "Custom unsupported message\n"


def test_make_server_message_hook_sends_formatted_console_command(monkeypatch):
    calls = []
    server = SimpleNamespace(name="demo")
    runtime_module = SimpleNamespace(
        send_to_server=lambda server_obj, payload: calls.append((server_obj.name, payload))
    )

    message = gamemodule_common.make_server_message_hook(
        command="say",
        runtime_module=runtime_module,
    )

    message(server, "hello world")

    assert calls == [("demo", "\nsay hello world\n")]


def test_make_steamcmd_install_hook_creates_directory_and_downloads(tmp_path):
    install_dir = tmp_path / "server"
    downloads = []
    server = SimpleNamespace(data=DummyData(dir=str(install_dir)))
    steamcmd_module = SimpleNamespace(
        download=lambda path, app_id, anon, validate=True, **kwargs: downloads.append(
            (path, app_id, anon, validate, kwargs)
        )
    )

    install = gamemodule_common.make_steamcmd_install_hook(
        steamcmd_module=steamcmd_module,
        steam_app_id=321,
        steam_anonymous_login_possible=True,
        download_kwargs={"force_windows": True},
    )

    install(server)

    assert install_dir.is_dir()
    assert downloads == [(str(install_dir), 321, True, False, {"force_windows": True})]


def test_make_steamcmd_update_hook_downloads_and_optionally_restarts(tmp_path):
    calls = []
    downloads = []
    server = SimpleNamespace(
        data=DummyData(dir=str(tmp_path)),
        stop=lambda: calls.append("stop"),
        start=lambda: calls.append("start"),
    )
    steamcmd_module = SimpleNamespace(
        download=lambda path, app_id, anon, validate=True, **kwargs: downloads.append(
            (path, app_id, anon, validate, kwargs)
        )
    )
    synced = []

    update = gamemodule_common.make_steamcmd_update_hook(
        steamcmd_module=steamcmd_module,
        steam_app_id=123,
        steam_anonymous_login_possible=False,
        sync_server_config=lambda current_server: synced.append(current_server.data["dir"]),
        download_kwargs={"force_windows": True},
    )

    update(server, validate=True, restart=True)

    assert calls == ["stop", "start"]
    assert downloads == [(str(tmp_path), 123, False, True, {"force_windows": True})]
    assert synced == [str(tmp_path)]


def test_make_steamcmd_update_hook_skips_sync_when_install_root_missing(tmp_path):
    missing_dir = tmp_path / "missing"
    downloads = []
    server = SimpleNamespace(
        data=DummyData(dir=str(missing_dir)),
        stop=lambda: None,
        start=lambda: None,
    )
    steamcmd_module = SimpleNamespace(
        download=lambda path, app_id, anon, validate=True, **kwargs: downloads.append(
            (path, app_id, anon, validate, kwargs)
        )
    )
    synced = []

    update = gamemodule_common.make_steamcmd_update_hook(
        steamcmd_module=steamcmd_module,
        steam_app_id=456,
        steam_anonymous_login_possible=True,
        sync_server_config=lambda _current_server: synced.append("called"),
    )

    update(server, validate=False, restart=False)

    assert downloads == [(str(missing_dir), 456, True, False, {})]
    assert synced == []