import sys
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import server.server as server_module
from server.settable_keys import SettingSpec


class DummyData(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved = 0

    def save(self):
        self.saved += 1

    def set_secret_keys(self, keys, secrets_filename):
        pass

    def prettydump(self):
        return '{"ok": true}'


class DummyModule:
    commands = ("custom",)
    command_args = {
        "setup": None,
        "custom": "custom-args",
    }
    command_descriptions = {
        "setup": "extra setup details",
        "custom": "custom description",
    }
    max_stop_wait = 1

    def __init__(self):
        self.calls = []

    def configure(self, server, ask, *args, **kwargs):
        self.calls.append(("configure", ask, args, kwargs))
        return ("configured",), {"flag": True}

    def install(self, server, *args, **kwargs):
        self.calls.append(("install", args, kwargs))

    def get_start_command(self, server, *args, **kwargs):
        self.calls.append(("get_start_command", args, kwargs))
        return ["run", "server"], "/srv/server"

    def do_stop(self, server, minute, *args, **kwargs):
        self.calls.append(("do_stop", minute, args, kwargs))

    def status(self, server, verbose, *args, **kwargs):
        self.calls.append(("status", verbose, args, kwargs))

    def message(self, server, *args, **kwargs):
        self.calls.append(("message", args, kwargs))

    def backup(self, server, *args, **kwargs):
        self.calls.append(("backup", args, kwargs))

    def checkvalue(self, server, key, *args, **kwargs):
        self.calls.append(("checkvalue", key, args, kwargs))
        return "value"


def make_server(module=None, data=None, name="alpha"):
    srv = server_module.Server.__new__(server_module.Server)
    srv.name = name
    srv.module = module or DummyModule()
    srv.data = data or DummyData()
    return srv


def test_findmodule_returns_module_after_alias_resolution(monkeypatch):
    real_module = SimpleNamespace(__file__="/tmp/real.py")
    imports = []

    class FakeCatalog:
        def resolve(self, name):
            assert name == "real"
            return "real"

    def fake_import(name):
        imports.append(name)
        if name.endswith(".real"):
            return real_module
        raise ImportError("missing")

    monkeypatch.setattr(server_module, "MODULE_CATALOG", FakeCatalog(), raising=False)
    monkeypatch.setattr(server_module, "import_module", fake_import)
    monkeypatch.setattr(server_module.runtime_module, "ensure_runtime_hooks", lambda module: None)
    monkeypatch.setattr(server_module, "SERVERMODULEPACKAGE", "gamemodules.")

    resolved_name, resolved_module = server_module._findmodule("real")

    assert resolved_name == "real"
    assert resolved_module is real_module
    assert imports == ["gamemodules.real"]


def test_findmodule_resolves_alias_through_catalog(monkeypatch):
    real_module = SimpleNamespace(__file__="/tmp/real.py")

    class FakeCatalog:
        def resolve(self, name):
            assert name == "tf2server"
            return "teamfortress2"

    def fake_import(name):
        if name != "gamemodules.teamfortress2":
            raise ImportError(name)
        return real_module

    monkeypatch.setattr(server_module, "MODULE_CATALOG", FakeCatalog(), raising=False)
    monkeypatch.setattr(server_module, "import_module", fake_import)
    monkeypatch.setattr(server_module.runtime_module, "ensure_runtime_hooks", lambda module: None)
    monkeypatch.setattr(server_module, "SERVERMODULEPACKAGE", "gamemodules.")

    resolved_name, resolved_module = server_module._findmodule("tf2server")

    assert resolved_name == "teamfortress2"
    assert resolved_module is real_module


def test_load_disabled_servers_parses_reasons(monkeypatch, tmp_path):
    disabled_path = tmp_path / "disabled_servers.conf"
    disabled_path.write_text(
        "# comment\n"
        "bf1942server\tDownload domain is dead\n"
        "minecraft.bedrock\tSetup hangs\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(server_module, "_DISABLED_SERVERS_PATH", str(disabled_path))

    assert server_module._load_disabled_servers() == {
        "bf1942server": "Download domain is dead",
        "minecraft.bedrock": "Setup hangs",
    }


def test_findmodule_rejects_disabled_canonical_module_before_import(monkeypatch):
    class FakeCatalog:
        def resolve(self, name):
            assert name == "tf2server"
            return "teamfortress2"

    monkeypatch.setattr(server_module, "MODULE_CATALOG", FakeCatalog(), raising=False)
    monkeypatch.setattr(
        server_module,
        "_load_disabled_servers",
        lambda: {"teamfortress2": "Known-broken in CI"},
    )

    def fail_import(_name):
        raise AssertionError("disabled module should not be imported")

    monkeypatch.setattr(server_module, "import_module", fail_import)

    with pytest.raises(server_module.ServerError) as exc_info:
        server_module._findmodule("tf2server")

    message = str(exc_info.value)
    assert "teamfortress2" in message
    assert "Known-broken in CI" in message
    assert "open an issue or submit a pull request" in message


def test_server_init_creates_new_datastore_and_saves(monkeypatch, tmp_path):
    created = {}

    class FakeStore(DummyData):
        def __init__(self, filename, payload=None):
            super().__init__(payload or {})
            created["filename"] = filename

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(server_module.data, "JSONDataStore", FakeStore)
    monkeypatch.setattr(server_module, "_findmodule", lambda name: (name, SimpleNamespace(commands=(), command_args={}, command_descriptions={})))

    srv = server_module.Server("alpha", "minecraft.vanilla")

    assert created["filename"].endswith("alpha.json")
    assert srv.data["module"] == "minecraft.vanilla"
    assert srv.data.saved == 1


def test_server_init_persists_canonical_name_when_created_from_alias(monkeypatch, tmp_path):
    class FakeStore(DummyData):
        def __init__(self, filename, payload=None):
            super().__init__(payload or {})

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(server_module.data, "JSONDataStore", FakeStore)
    monkeypatch.setattr(
        server_module,
        "_findmodule",
        lambda name: (
            "teamfortress2",
            SimpleNamespace(commands=(), command_args={}, command_descriptions={}),
        ),
    )

    srv = server_module.Server("alpha", "tf2server")

    assert srv.data["module"] == "teamfortress2"
    assert srv.data.saved == 1


def test_server_init_updates_redirected_module_name(monkeypatch, tmp_path, capsys):
    class FakeStore(DummyData):
        def __init__(self, filename, payload=None):
            super().__init__({"module": "alias"})

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(server_module.data, "JSONDataStore", FakeStore)
    monkeypatch.setattr(server_module, "_findmodule", lambda name: ("real.module", SimpleNamespace(commands=(), command_args={}, command_descriptions={})))

    srv = server_module.Server("alpha")

    assert srv.data["module"] == "real.module"
    assert srv.data.saved == 1
    assert "Module has been redirected" in capsys.readouterr().out


def test_server_init_rewrites_saved_alias_to_canonical_name(monkeypatch, tmp_path, capsys):
    class FakeStore(DummyData):
        def __init__(self, filename, payload=None):
            super().__init__({"module": "tf2"})

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(server_module.data, "JSONDataStore", FakeStore)
    monkeypatch.setattr(
        server_module,
        "_findmodule",
        lambda name: (
            "teamfortress2",
            SimpleNamespace(commands=(), command_args={}, command_descriptions={}),
        ),
    )

    srv = server_module.Server("alpha")

    assert srv.data["module"] == "teamfortress2"
    assert srv.data.saved == 1
    assert "Module has been redirected" in capsys.readouterr().out


def test_server_init_syncs_runtime_metadata_from_module_hook(monkeypatch, tmp_path):
    class FakeSection(dict):
        def getsection(self, key):
            return self.get(key, FakeSection())

    class FakeStore(DummyData):
        def __init__(self, filename, payload=None):
            super().__init__(payload or {})

    module = SimpleNamespace(
        commands=(),
        command_args={},
        command_descriptions={},
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "minecraft",
            "java": 17,
        },
    )

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(server_module.data, "JSONDataStore", FakeStore)
    monkeypatch.setattr(server_module, "_findmodule", lambda name: (name, module))
    monkeypatch.setattr(
        server_module.runtime_module.settings,
        "_user",
        FakeSection({"runtime": FakeSection({"backend": "docker"})}),
        raising=False,
    )

    srv = server_module.Server("alpha", "minecraft.vanilla")

    assert srv.data["runtime"] == "docker"
    assert srv.data["runtime_family"] == "java"
    assert srv.data["java_major"] == 17


def test_get_commands_args_and_descriptions_merge_module_data():
    srv = make_server()

    commands = srv.get_commands()
    description = srv.get_command_description("setup")

    assert "custom" in commands
    assert srv.get_command_args("doctor") is not None
    assert "extra setup details" in description
    assert srv.get_command_args("custom") == "custom-args"


def test_run_command_dispatches_builtin_and_custom_methods(monkeypatch):
    srv = make_server()
    calls = []
    monkeypatch.setattr(srv, "setup", lambda *args, **kwargs: calls.append(("setup", args, kwargs)))
    monkeypatch.setattr(srv, "connect", lambda *args, **kwargs: calls.append(("connect", args, kwargs)))
    monkeypatch.setattr(srv, "dump", lambda *args, **kwargs: calls.append(("dump", args, kwargs)))
    monkeypatch.setattr(srv, "doctor", lambda *args, **kwargs: calls.append(("doctor", args, kwargs)))
    monkeypatch.setattr(srv, "doset", lambda *args, **kwargs: calls.append(("set", args, kwargs)))
    srv.module.command_functions = {"custom": lambda server, *args, **kwargs: calls.append(("custom", args, kwargs))}

    srv.run_command("setup", 1, flag=True)
    srv.run_command("message", "hello")
    srv.run_command("backup", "nightly")
    srv.run_command("connect")
    srv.run_command("dump")
    srv.run_command("doctor")
    srv.run_command("set", "path", "value")
    srv.run_command("custom", 9)

    assert ("setup", (1,), {"flag": True}) in calls
    assert ("custom", (9,), {}) in calls
    assert ("set", ("path", "value"), {}) in calls
    assert ("message", (("hello",), {})) not in calls
    assert any(call[0] == "connect" for call in calls)
    assert any(call[0] == "doctor" for call in calls)
    assert any(entry[0] == "message" for entry in srv.module.calls)
    assert any(entry[0] == "backup" for entry in srv.module.calls)


def test_run_command_rejects_unknown_command():
    srv = make_server()
    srv.module.command_functions = {}

    with pytest.raises(server_module.ServerError, match="Unknown command"):
        srv.run_command("missing")


def test_setup_passes_configure_results_to_install():
    srv = make_server()

    srv.setup("arg", ask=False, extra=True)

    assert srv.module.calls[0] == ("configure", False, ("arg",), {"extra": True})
    assert ("install", ("configured",), {"flag": True}) in srv.module.calls


def test_setup_syncs_runtime_metadata_after_port_resolution_and_before_install(monkeypatch):
    events = []
    srv = make_server()

    srv.module.configure = lambda server, ask, *args, **kwargs: (
        events.append("configure") or (("configured",), {"flag": True})
    )
    srv.module.install = lambda server, *args, **kwargs: events.append("install")
    monkeypatch.setattr(
        server_module.runtime_module,
        "sync_runtime_metadata",
        lambda server, save=False: events.append("sync"),
    )
    monkeypatch.setattr(
        srv,
        "_resolve_setup_port_claims",
        lambda explicit_keys: events.append("resolve"),
    )

    srv.setup("arg", ask=False, extra=True)

    assert events == ["configure", "sync", "resolve", "sync", "install", "sync"]


def test_start_runs_pre_and_post_hooks_and_starts_screen(monkeypatch):
    events = []
    srv = make_server()
    srv.module.prestart = lambda *args, **kwargs: events.append(("prestart", args, kwargs))
    srv.module.poststart = lambda *args, **kwargs: events.append(("poststart", args, kwargs))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: False)
    monkeypatch.setattr(server_module.screen, "start_screen", lambda name, cmd, cwd=None: events.append(("start_screen", name, cmd, cwd)))

    srv.start("now", force=True)

    assert events[0] == ("prestart", (srv, "now"), {"force": True})
    assert events[1] == ("start_screen", "alpha", ["run", "server"], "/srv/server")
    assert events[2] == ("poststart", (srv, "now"), {"force": True})


def test_start_rejects_already_running_server(monkeypatch):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: True)

    with pytest.raises(server_module.ServerError, match="already running"):
        srv.start()


def test_stop_requests_module_stop_until_server_exits(monkeypatch):
    srv = make_server()
    states = iter([True, False])
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: next(states))
    monkeypatch.setattr(server_module.time, "sleep", lambda seconds: None)

    srv.stop()

    assert srv.module.calls == [("do_stop", 0, (), {})]


def test_stop_kills_server_after_timeout(monkeypatch):
    srv = make_server()
    states = iter([True] * 20)
    sent = []
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: next(states))
    monkeypatch.setattr(server_module.screen, "send_to_screen", lambda name, cmd: sent.append((name, cmd)))
    monkeypatch.setattr(server_module.time, "sleep", lambda seconds: None)

    with pytest.raises(server_module.ServerError, match="can't kill server"):
        srv.stop()

    assert sent == [("alpha", ["quit"])]


def test_stop_uses_runtime_kill_immediately_for_docker_stop_mode(monkeypatch):
    srv = make_server()
    runtime = SimpleNamespace(
        is_running=MagicMock(side_effect=[True, False]),
        kill=MagicMock(),
    )
    monkeypatch.setattr(server_module.runtime_module, "get_runtime", lambda server: runtime)
    monkeypatch.setattr(
        server_module.runtime_module,
        "resolve_runtime_metadata",
        lambda server: {"stop_mode": "docker-stop"},
    )

    srv.stop()

    runtime.kill.assert_called_once_with(srv)
    assert srv.module.calls == []


def test_status_connect_and_dump_use_screen_and_output(monkeypatch, capsys):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: True)
    monkeypatch.setattr(server_module.screen, "connect_to_screen", lambda name: capsys.readouterr() or None)

    srv.status(verbose=1)
    srv.dump()

    out = capsys.readouterr().out
    assert "Server is running as screen session exists" in out
    assert '{"ok": true}' in out
    assert any(entry[0] == "status" for entry in srv.module.calls)


def test_doctor_prints_runtime_report(monkeypatch, capsys):
    srv = make_server()

    monkeypatch.setattr(
        server_module.runtime_module,
        "print_runtime_doctor_report",
        lambda server: print("Runtime doctor for " + server.name),
    )

    srv.doctor()

    assert "Runtime doctor for alpha" in capsys.readouterr().out


def test_doset_updates_nested_data_and_saves():
    srv = make_server(data=DummyData({"existing": {"items": []}}))

    srv.doset("existing.items.APPEND", "new")

    assert srv.data["existing"]["items"] == ["value"]
    assert srv.data.saved == 1


def test_doset_lists_schema_backed_keys(capsys):
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "zzz": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap"),
            description="Current map",
            value_type="string",
            storage_key="startmap",
            examples=("cp_badlands",),
        ),
        "aaa": SettingSpec(
            canonical_key="rconpassword",
            aliases=("rconpass",),
            description="RCON password",
            value_type="string",
            secret=True,
        ),
    }

    srv.doset(list_settings=True)

    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line]
    assert lines[0].startswith("map ")
    assert lines[1].startswith("rconpassword ")
    assert "gamemap" in out
    assert "startmap" in out
    assert "rconpassword" in out


def test_doset_lists_schema_backed_keys_verbose(capsys):
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap"),
            description="Current map",
            value_type="string",
            storage_key="startmap",
            examples=("cp_badlands",),
        ),
        "rconpassword": SettingSpec(
            canonical_key="rconpassword",
            aliases=("rconpass",),
            description="RCON password",
            value_type="string",
            secret=True,
        ),
    }

    srv.doset(list_settings=True, verbose=True)

    out = capsys.readouterr().out
    assert "map" in out
    assert "gamemap" in out
    assert "startmap" in out
    assert "rconpassword" in out
    assert "storage key=startmap" in out
    assert "type=string" in out
    assert "applies to=datastore" in out
    assert "secret" in out
    assert "examples=cp_badlands" in out


def test_doset_describes_schema_backed_key(capsys):
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap", "level"),
            description="Current map",
            value_type="string",
            storage_key="startmap",
            examples=("cp_badlands",),
        )
    }

    srv.doset("gamemap", describe=True)

    out = capsys.readouterr().out
    assert "Canonical key: map" in out
    assert "Storage key: startmap" in out
    assert "Aliases: gamemap, startmap, level" in out
    assert "Examples: cp_badlands" in out


def test_doset_lists_common_setting_aliases(capsys):
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "servername": SettingSpec(
            canonical_key="servername",
            description="Current public name",
            value_type="string",
        )
    }

    srv.doset(list_settings=True)

    out = capsys.readouterr().out
    assert "hostname" in out
    assert "name" in out


def test_doset_describe_uses_common_alias_resolution(capsys):
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "servername": SettingSpec(
            canonical_key="servername",
            description="Current public name",
            value_type="string",
        )
    }

    srv.doset("hostname", describe=True)

    out = capsys.readouterr().out
    assert "Requested key: hostname" in out
    assert "Canonical key: servername" in out
    assert "Aliases: hostname, name" in out


def test_doset_lists_values_for_schema_backed_key(capsys):
    srv = make_server(data=DummyData({}))
    seen = {}
    srv.module.setting_schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap"),
            description="Current map",
            value_type="string",
            storage_key="startmap",
        )
    }

    def list_setting_values(server, canonical_key):
        seen["server"] = server
        seen["canonical_key"] = canonical_key
        return ["cp_badlands", "cp_dustbowl"]

    srv.module.list_setting_values = list_setting_values

    srv.doset("gamemap", values=True)

    out = capsys.readouterr().out
    assert "cp_badlands" in out
    assert "cp_dustbowl" in out
    assert seen == {"server": srv, "canonical_key": "map"}


def test_doset_resolves_alias_to_storage_key_before_parse_and_check(monkeypatch):
    srv = make_server(data=DummyData({"startmap": "old"}))
    seen = {}
    srv.module.setting_schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap"),
            description="Current map",
            value_type="string",
            storage_key="startmap",
        )
    }

    def fake_parsekey(raw_key):
        seen["parsekey"] = raw_key
        return iter(((dict,), ("startmap",)))

    def checkvalue(server, key, *args, **kwargs):
        seen["checkvalue_key"] = key
        seen["checkvalue_args"] = args
        return str(args[0])

    monkeypatch.setattr(server_module, "_parsekey", fake_parsekey)
    srv.module.checkvalue = checkvalue

    srv.doset("gamemap", "cp_badlands")

    assert seen == {
        "parsekey": "startmap",
        "checkvalue_key": ("startmap",),
        "checkvalue_args": ("cp_badlands",),
    }
    assert srv.data["startmap"] == "cp_badlands"


def test_doset_rejects_ambiguous_schema_aliases():
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap",),
            description="Current map",
            value_type="string",
            storage_key="startmap",
        ),
        "game_map": SettingSpec(
            canonical_key="game_map",
            aliases=("gamemap",),
            description="Alternate map",
            value_type="string",
            storage_key="mapname",
        ),
    }

    with pytest.raises(server_module.ServerError, match="Ambiguous setting key"):
        srv.doset("gamemap", "cp_badlands")


def test_doset_rejects_malformed_setting_schema():
    srv = make_server(data=DummyData({}))
    srv.module.setting_schema = ["not", "a", "mapping"]

    with pytest.raises(server_module.ServerError, match="setting_schema must be a mapping"):
        srv.doset(list_settings=True)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"describe": True},
        {"values": True},
        {},
    ),
)
def test_doset_rejects_missing_key_for_discovery_and_write_modes(kwargs):
    srv = make_server(data=DummyData({}))

    with pytest.raises(server_module.ServerError, match="requires a key"):
        srv.doset(**kwargs)


def test_doset_calls_module_postset_with_updated_data(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015}))
    seen = {}

    def postset(server, key, *args, **kwargs):
        seen["server"] = server
        seen["key"] = key
        seen["port"] = server.data["port"]

    srv.module.checkvalue = lambda server, key, *args, **kwargs: int(args[0])
    srv.module.postset = postset
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [])
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    srv.doset("port", "27030")

    assert seen == {
        "server": srv,
        "key": ("port",),
        "port": 27030,
    }
    assert srv.data.saved == 1


def test_doset_runs_sync_server_config_for_matching_key(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015}))
    seen = {}

    def sync_server_config(server):
        seen["server"] = server
        seen["port"] = server.data["port"]

    srv.module.checkvalue = lambda server, key, *args, **kwargs: int(args[0])
    srv.module.sync_server_config = sync_server_config
    srv.module.config_sync_keys = ("port",)
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [])
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    srv.doset("port", "27030")

    assert seen == {"server": srv, "port": 27030}
    assert srv.data.saved == 1


def test_doset_skips_sync_server_config_for_non_matching_key():
    srv = make_server(data=DummyData({"port": 27015, "hostname": "old"}))
    calls = []

    def sync_server_config(server):
        calls.append(server.data.copy())

    srv.module.checkvalue = lambda server, key, *args, **kwargs: args[0]
    srv.module.sync_server_config = sync_server_config
    srv.module.config_sync_keys = ("port",)

    srv.doset("hostname", "new")

    assert calls == []
    assert srv.data["hostname"] == "new"


def test_doset_skips_sync_server_config_without_explicit_config_keys():
    srv = make_server(data=DummyData({"hostname": "old"}))
    calls = []

    def sync_server_config(server):
        calls.append(server.data.copy())

    srv.module.checkvalue = lambda server, key, *args, **kwargs: args[0]
    srv.module.sync_server_config = sync_server_config

    srv.doset("hostname", "new")

    assert calls == []
    assert srv.data["hostname"] == "new"


def test_doset_rewrites_real_non_valve_config_file_via_alias(monkeypatch, tmp_path):
    sys.modules.pop("gamemodules.stnserver", None)
    with patch.dict(
        "sys.modules",
        {
            "screen": MagicMock(),
            "utils.backups": MagicMock(),
            "utils.backups.backups": MagicMock(),
            "utils.steamcmd": MagicMock(),
        },
    ):
        stnserver_module = import_module("gamemodules.stnserver")

    config_dir = tmp_path / "Config"
    config_dir.mkdir()
    config_path = config_dir / "ServerConfig.txt"
    config_path.write_text("Port=8888\nOtherKey=value\n", encoding="utf-8")

    srv = make_server(
        module=stnserver_module,
        data=DummyData(
            {
                "port": 8888,
                "dir": str(tmp_path),
                "configfile": "Config/ServerConfig.txt",
            }
        ),
    )

    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: [],
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "recommend_shift",
        lambda server, max_offset=100, base_overrides=None: None,
    )

    srv.doset("gameport", "9999")

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "Port=9999",
        "OtherKey=value",
    ]
    assert srv.data["port"] == 9999
    assert srv.data.saved == 1


def test_doset_rejects_colliding_port_change_and_recommends_group_shift(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015, "queryport": 27016}))
    srv.module.checkvalue = lambda server, key, *args, **kwargs: int(args[0])
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [conflict])
    monkeypatch.setattr(
        server_module.port_manager,
        "recommend_shift",
        lambda server, max_offset=100, base_overrides=None: server_module.port_manager.PortShiftRecommendation(
            offset=2,
            values={"port": 27017, "queryport": 27018},
        ),
    )

    with pytest.raises(server_module.ServerError, match="Recommended free port set"):
        srv.doset("port", "27015")


def test_doset_marks_port_keys_as_explicit(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015}))
    srv.module.checkvalue = lambda server, key, *args, **kwargs: int(args[0])
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [])
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    srv.doset("port", "27030")

    assert srv.data["port"] == 27030
    assert srv.data["port_claim_policy"]["port"] == "explicit"


def test_doset_uses_runtime_validation_for_runtime_metadata(monkeypatch):
    srv = make_server(data=DummyData({"runtime": "docker", "runtime_family": "java"}))

    def fail_checkvalue(server, key, *args, **kwargs):
        raise AssertionError("module.checkvalue should not be used for runtime keys")

    srv.module.checkvalue = fail_checkvalue
    monkeypatch.setattr(
        server_module.runtime_module,
        "sync_runtime_metadata",
        lambda server, save=False: server.data.update({"env": {"ALPHAGSM_JAVA_MAJOR": "25"}}),
    )

    srv.doset("image", "eclipse-temurin:25-jre")
    srv.doset("java_major", "25")

    assert srv.data["image"] == "eclipse-temurin:25-jre"
    assert srv.data["java_major"] == 25
    assert srv.data["env"] == {"ALPHAGSM_JAVA_MAJOR": "25"}


def test_doset_rejects_invalid_runtime_metadata_value():
    srv = make_server(data=DummyData({"runtime": "docker", "runtime_family": "java"}))

    with pytest.raises(server_module.ServerError, match="Unsupported stop_mode"):
        srv.doset("stop_mode", "halt-now")


def test_doset_rejects_colliding_bindaddress_change(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015, "bindaddress": "127.0.0.1"}))
    srv.module.checkvalue = lambda server, key, *args, **kwargs: args[0]
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    seen = {}

    def fake_detect_conflicts(server, overrides=None, include_live=True):
        seen["bindaddress"] = server.data["bindaddress"]
        return [conflict]

    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", fake_detect_conflicts)
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    with pytest.raises(server_module.ServerError, match="conflicts"):
        srv.doset("bindaddress", "0.0.0.0")

    assert seen["bindaddress"] == "0.0.0.0"


def test_doset_rejects_colliding_runtime_ports_append(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015, "ports": []}))
    runtime_port = {"host": 27016, "container": 27016, "protocol": "udp"}
    srv.module.checkvalue = lambda server, key, *args, **kwargs: runtime_port
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("external", "0.0.0.0", 27016, "runtime:ports"),
        "runtime:ports conflicts with bravo:runtime:ports on 0.0.0.0:27016",
        managed_server="bravo",
    )
    seen = {}

    def fake_detect_conflicts(server, overrides=None, include_live=True):
        seen["ports"] = list(server.data["ports"])
        return [conflict]

    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", fake_detect_conflicts)
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    with pytest.raises(server_module.ServerError, match="runtime:ports"):
        srv.doset("ports.APPEND", runtime_port)

    assert seen["ports"] == [runtime_port]
    assert srv.data["ports"] == []


def test_setup_auto_shifts_default_owned_port_group_and_prints_warning(monkeypatch, capsys):
    srv = make_server(
        data=DummyData({"port": 27015, "queryport": 27016}),
        module=DummyModule(),
    )
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [conflict])
    monkeypatch.setattr(
        server_module.port_manager,
        "recommend_shift",
        lambda server, max_offset=100, base_overrides=None: server_module.port_manager.PortShiftRecommendation(
            offset=2,
            values={"port": 27017, "queryport": 27018},
        ),
    )

    srv.setup(ask=False)

    assert srv.data["port"] == 27017
    assert srv.data["queryport"] == 27018
    assert srv.data["port_claim_policy"] == {
        "port": "default",
        "queryport": "default",
    }
    assert "shifted claimed port set" in capsys.readouterr().out


def test_setup_marks_port_arguments_as_explicit_and_rejects_collision(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015, "queryport": 27016}), module=DummyModule())
    srv.get_command_args = lambda command: server_module.CmdSpec(
        optionalarguments=(
            server_module.ArgSpec("port", "Primary server port", int),
            server_module.ArgSpec("dir", "Install directory", str),
        )
    )
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [conflict])
    monkeypatch.setattr(
        server_module.port_manager,
        "recommend_shift",
        lambda server, max_offset=100, base_overrides=None: server_module.port_manager.PortShiftRecommendation(
            offset=2,
            values={"port": 27017, "queryport": 27018},
        ),
    )

    with pytest.raises(server_module.ServerError, match="Recommended free port set"):
        srv.setup(27015, "/srv/test", ask=False)

    assert srv.data["port_claim_policy"]["port"] == "explicit"


def test_setup_treats_interactively_changed_port_as_explicit(monkeypatch):
    srv = make_server(data=DummyData({"port": 27014, "queryport": 27016}), module=DummyModule())

    def configure(server, ask, *args, **kwargs):
        server.data["port"] = 27015
        return (), {}

    srv.module.configure = configure
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: [conflict],
    )
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    with pytest.raises(server_module.ServerError, match="explicit port choices conflict"):
        srv.setup(ask=True)

    assert srv.data["port_claim_policy"]["port"] == "explicit"


def test_setup_persists_explicit_policy_before_raising_on_explicit_conflict(monkeypatch):
    srv = make_server(data=DummyData({"port": 27015, "queryport": 27016}), module=DummyModule())
    srv.get_command_args = lambda command: server_module.CmdSpec(
        optionalarguments=(server_module.ArgSpec("port", "Primary server port", int),)
    )
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: [conflict],
    )
    monkeypatch.setattr(server_module.port_manager, "recommend_shift", lambda server, max_offset=100, base_overrides=None: None)

    with pytest.raises(server_module.ServerError):
        srv.setup(27015, ask=False)

    assert srv.data["port_claim_policy"]["port"] == "explicit"
    assert srv.data.saved >= 1


def test_setup_preserves_existing_explicit_port_policy_when_args_omitted(monkeypatch):
    srv = make_server(
        data=DummyData(
            {
                "port": 27015,
                "queryport": 27016,
                "port_claim_policy": {"port": "explicit"},
            }
        ),
        module=DummyModule(),
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: [],
    )

    srv.setup(ask=False)

    assert srv.data["port_claim_policy"] == {
        "port": "explicit",
        "queryport": "default",
    }


def test_setup_rejects_conflict_for_previously_explicit_port_even_without_current_arg(monkeypatch):
    srv = make_server(
        data=DummyData(
            {
                "port": 27015,
                "queryport": 27016,
                "port_claim_policy": {"port": "explicit"},
            }
        ),
        module=DummyModule(),
    )
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: [conflict],
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "recommend_shift",
        lambda server, max_offset=100, base_overrides=None: server_module.port_manager.PortShiftRecommendation(
            offset=2,
            values={"port": 27017, "queryport": 27018},
        ),
    )

    with pytest.raises(server_module.ServerError, match="explicit port choices conflict"):
        srv.setup(ask=False)


def test_start_checks_port_manager_before_prestart(monkeypatch):
    events = []
    srv = make_server()
    srv.module.prestart = lambda *args, **kwargs: events.append("prestart")
    monkeypatch.setattr(
        server_module.runtime_module,
        "get_runtime",
        lambda server: SimpleNamespace(
            is_running=lambda current: False,
            start=lambda current, *args, **kwargs: events.append("runtime.start"),
        ),
    )
    monkeypatch.setattr(
        server_module.port_manager,
        "detect_conflicts",
        lambda server, overrides=None, include_live=True: events.append("port-check") or [],
    )

    srv.start()

    assert events == ["port-check", "prestart", "runtime.start"]


def test_start_fails_when_claimed_ports_are_busy(monkeypatch):
    srv = make_server()
    conflict = server_module.port_manager.PortConflict(
        "managed",
        server_module.port_manager.PortEndpoint("internal", "0.0.0.0", 27015, "port"),
        "port conflicts with bravo:port on 0.0.0.0:27015",
        managed_server="bravo",
    )
    monkeypatch.setattr(
        server_module.runtime_module,
        "get_runtime",
        lambda server: SimpleNamespace(
            is_running=lambda current: False,
            start=lambda current, *args, **kwargs: None,
        ),
    )
    monkeypatch.setattr(server_module.port_manager, "detect_conflicts", lambda server, overrides=None, include_live=True: [conflict])
    monkeypatch.setattr(server_module.port_manager, "describe_conflicts", lambda conflicts: "managed server bravo")

    with pytest.raises(server_module.ServerError, match="managed server bravo"):
        srv.start()


def test_parse_helpers_cover_keys_and_multi_server_commands():
    assert server_module._parsekeyelement("APPEND") == (list, None)
    assert server_module._parsekeyelement("2") == (list, 2)
    assert server_module._parsekeyelement("name") == (dict, "name")
    assert list(server_module._parsekey("root.0.APPEND")) == [(dict, list, list), ("root", 0, None)]
    assert server_module._parsecmd(["alphagsm", "2", "a", "b", "start"]) == ["alphagsm", ["a", "b"], "start"]
    assert server_module._parsecmd(["alphagsm", "solo", "start"]) == ["alphagsm", ["solo"], "start"]


def test_activate_updates_crontab_and_can_start_server(monkeypatch):
    srv = make_server()
    started = []

    class FakeJob:
        def __init__(self, command):
            self.command = command
            self.slices = SimpleNamespace(special="@reboot")

        def is_enabled(self):
            return True

        def every_reboot(self):
            return None

    class FakeCronTab(list):
        def __init__(self, jobs):
            super().__init__(jobs)
            self.written = False
            self.new_job = None

        def write(self):
            self.written = True

        def new(self, command):
            self.new_job = FakeJob(command)
            self.append(self.new_job)
            return self.new_job

    cron = FakeCronTab([FakeJob("/usr/bin/alphagsm 1 other start")])
    monkeypatch.setattr(server_module.crontab, "CronTab", lambda user=True: cron)
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: False)
    monkeypatch.setattr(server_module, "_parsecmd", lambda cmd: [cmd[0], [cmd[2]], cmd[3]])
    monkeypatch.setattr("core.program.PATH", "/usr/bin/alphagsm")
    monkeypatch.setattr(srv, "start", lambda: started.append(True))

    srv.activate(start=True)

    assert cron.written is True
    assert cron.new_job is None
    assert "alpha" in cron[0].command
    assert started == [True]


def test_deactivate_removes_or_updates_jobs_and_can_stop_server(monkeypatch):
    srv = make_server()
    stopped = []

    class FakeJob:
        def __init__(self, command, servers):
            self.command = command
            self._servers = servers
            self.slices = SimpleNamespace(special="@reboot")

        def is_enabled(self):
            return True

    class FakeCronTab(list):
        def __init__(self, jobs):
            super().__init__(jobs)
            self.removed = []
            self.written = False

        def remove(self, job):
            self.removed.append(job)
            self[:] = [entry for entry in self if entry is not job]

        def write(self):
            self.written = True

    job = FakeJob("/usr/bin/alphagsm 2 alpha beta start", ["alpha", "beta"])
    cron = FakeCronTab([job])
    monkeypatch.setattr(server_module.crontab, "CronTab", lambda user=True: cron)
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: True)
    monkeypatch.setattr("core.program.PATH", "/usr/bin/alphagsm")
    monkeypatch.setattr(server_module, "_parsecmd", lambda cmd: [cmd[0], ["alpha", "beta"], "start"])
    monkeypatch.setattr(srv, "stop", lambda: stopped.append(True))

    srv.deactivate(stop=True)

    assert cron.written is True
    assert stopped == [True]
    assert job.command == "/usr/bin/alphagsm 1 beta start"


# ---------------------------------------------------------------------------
# Tests for restart, kill, send, and logs commands
# ---------------------------------------------------------------------------


def test_restart_stops_then_starts(monkeypatch):
    srv = make_server()
    calls = []
    monkeypatch.setattr(srv, "stop", lambda *a, **kw: calls.append("stop"))
    monkeypatch.setattr(srv, "start", lambda *a, **kw: calls.append("start"))

    srv.restart()

    assert calls == ["stop", "start"]


def test_kill_sends_quit_and_succeeds(monkeypatch):
    srv = make_server()
    sent = []
    states = iter([True, False])
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: next(states))
    monkeypatch.setattr(server_module.screen, "send_to_screen", lambda name, cmd: sent.append((name, cmd)))
    monkeypatch.setattr(server_module.time, "sleep", lambda s: None)

    srv.kill()

    assert sent == [("alpha", ["quit"])]


def test_kill_raises_if_server_not_running(monkeypatch):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: False)

    with pytest.raises(server_module.ServerError, match="isn't running"):
        srv.kill()


def test_kill_raises_if_session_persists_after_quit(monkeypatch):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: True)
    monkeypatch.setattr(server_module.screen, "send_to_screen", lambda name, cmd: None)
    monkeypatch.setattr(server_module.time, "sleep", lambda s: None)

    with pytest.raises(server_module.ServerError, match="Could not kill"):
        srv.kill()


def test_send_sends_input_to_running_server(monkeypatch):
    srv = make_server()
    sent = []
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: True)
    monkeypatch.setattr(server_module.screen, "send_to_server", lambda name, text: sent.append((name, text)))

    srv.send("say hello")

    assert sent == [("alpha", "say hello\n")]


def test_send_raises_if_server_not_running(monkeypatch):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda name: False)

    with pytest.raises(server_module.ServerError, match="isn't running"):
        srv.send("say hello")


def test_logs_tails_logfile(monkeypatch, tmp_path):
    srv = make_server()
    log_file = tmp_path / "alpha.log"
    log_file.write_text("line1\nline2\nline3\n")
    monkeypatch.setattr(server_module.screen, "logpath", lambda name: str(log_file))
    ran = []

    def fake_run(cmd, check):
        ran.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(server_module.sp, "run", fake_run)

    srv.logs(lines=10)

    assert ran == [["tail", "-n", "10", str(log_file)]]


def test_logs_raises_if_no_log_file(monkeypatch, tmp_path):
    srv = make_server()
    monkeypatch.setattr(server_module.screen, "logpath", lambda name: str(tmp_path / "missing.log"))

    with pytest.raises(server_module.ServerError, match="No log file"):
        srv.logs()


def test_logs_raises_if_tail_fails(monkeypatch, tmp_path):
    srv = make_server()
    log_file = tmp_path / "alpha.log"
    log_file.write_text("data")
    monkeypatch.setattr(server_module.screen, "logpath", lambda name: str(log_file))

    def fake_run(cmd, check):
        return type("R", (), {"returncode": 1})()

    monkeypatch.setattr(server_module.sp, "run", fake_run)

    with pytest.raises(server_module.ServerError, match="Failed to read"):
        srv.logs()


# ---------------------------------------------------------------------------
# restore
# ---------------------------------------------------------------------------

def _make_backup_entry(tag, dt_str, fname):
    import datetime
    return (tag, datetime.datetime.fromisoformat(dt_str), fname)


def test_restore_lists_backups_when_no_argument(monkeypatch, capsys):
    entries = [
        _make_backup_entry("default", "2024-01-01 00:00:00", "default 2024.01.01 00:00:00.000000.zip"),
        _make_backup_entry("default", "2024-06-15 12:00:00", "default 2024.06.15 12:00:00.000000.zip"),
    ]
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.backups
    import sys, types
    fake_bu = types.ModuleType("utils.backups.backups")
    fake_bu.list_backups = lambda d: entries
    monkeypatch.setattr(utils.backups, "backups", fake_bu)
    monkeypatch.setitem(sys.modules, "utils.backups.backups", fake_bu)

    srv.restore()

    out = capsys.readouterr().out
    assert "[0]" in out
    assert "[1]" in out
    assert "2024-01-01" in out


def test_restore_prints_message_when_no_backups_exist(monkeypatch, capsys):
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.backups
    import sys, types
    fake_bu = types.ModuleType("utils.backups.backups")
    fake_bu.list_backups = lambda d: []
    monkeypatch.setattr(utils.backups, "backups", fake_bu)
    monkeypatch.setitem(sys.modules, "utils.backups.backups", fake_bu)

    srv.restore()

    assert "No backups found" in capsys.readouterr().out


def test_restore_by_index_stops_running_server(monkeypatch):
    entries = [
        _make_backup_entry("default", "2024-01-01 00:00:00", "default 2024.01.01 00:00:00.000000.zip"),
    ]
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))
    calls = []

    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: True)
    monkeypatch.setattr(srv, "stop", lambda: calls.append("stop"))

    import utils.backups
    import sys, types
    fake_bu = types.ModuleType("utils.backups.backups")
    fake_bu.list_backups = lambda d: entries
    fake_bu.restore = lambda d, f: calls.append(("restore", f))
    monkeypatch.setattr(utils.backups, "backups", fake_bu)
    monkeypatch.setitem(sys.modules, "utils.backups.backups", fake_bu)

    srv.restore(backup="0")

    assert "stop" in calls
    assert ("restore", "default 2024.01.01 00:00:00.000000.zip") in calls


def test_restore_by_filename_skips_stop_when_not_running(monkeypatch):
    entries = [
        _make_backup_entry("default", "2024-01-01 00:00:00", "snap.zip"),
    ]
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))
    calls = []

    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)

    import utils.backups
    import sys, types
    fake_bu = types.ModuleType("utils.backups.backups")
    fake_bu.list_backups = lambda d: entries
    fake_bu.restore = lambda d, f: calls.append(("restore", f))
    monkeypatch.setattr(utils.backups, "backups", fake_bu)
    monkeypatch.setitem(sys.modules, "utils.backups.backups", fake_bu)

    srv.restore(backup="snap.zip")

    assert calls == [("restore", "snap.zip")]


def test_restore_raises_for_out_of_range_index(monkeypatch):
    entries = [
        _make_backup_entry("default", "2024-01-01 00:00:00", "snap.zip"),
    ]
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)

    import utils.backups
    import sys, types
    fake_bu = types.ModuleType("utils.backups.backups")
    fake_bu.list_backups = lambda d: entries
    monkeypatch.setattr(utils.backups, "backups", fake_bu)
    monkeypatch.setitem(sys.modules, "utils.backups.backups", fake_bu)

    with pytest.raises(server_module.ServerError, match="out of range"):
        srv.restore(backup="5")


# ---------------------------------------------------------------------------
# wipe
# ---------------------------------------------------------------------------

def test_wipe_raises_if_server_running(monkeypatch):
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: True)

    with pytest.raises(server_module.ServerError, match="Cannot wipe a running server"):
        srv.wipe()


def test_wipe_raises_if_no_wipe_support(monkeypatch):
    module = DummyModule()
    # DummyModule has no wipe or wipe_paths
    srv = make_server(module=module, data=DummyData({"dir": "/srv/game", "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)

    with pytest.raises(server_module.ServerError, match="not supported"):
        srv.wipe()


def test_wipe_calls_module_wipe_callable(monkeypatch):
    calls = []
    module = DummyModule()
    module.wipe = lambda server: calls.append("wipe")

    srv = make_server(module=module, data=DummyData({"dir": "/srv/game", "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)

    srv.wipe()

    assert calls == ["wipe"]


def test_wipe_removes_wipe_paths(monkeypatch, tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    world_dir = game_dir / "Saves"
    world_dir.mkdir()

    module = DummyModule()
    module.wipe_paths = ["Saves"]

    srv = make_server(module=module, data=DummyData({"dir": str(game_dir), "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)
    # Allow real sp.run so rm -rf actually runs
    srv.wipe()

    assert not world_dir.exists()


def test_wipe_raises_if_rm_fails(monkeypatch, tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    (game_dir / "Saves").mkdir()

    module = DummyModule()
    module.wipe_paths = ["Saves"]

    srv = make_server(module=module, data=DummyData({"dir": str(game_dir), "port": "27015"}))
    monkeypatch.setattr(server_module.screen, "check_screen_exists", lambda n: False)
    monkeypatch.setattr(
        server_module.sp,
        "run",
        lambda cmd, check: type("R", (), {"returncode": 1})(),
    )

    with pytest.raises(server_module.ServerError, match="Failed to remove"):
        srv.wipe()


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

def test_query_succeeds_via_a2s(monkeypatch, capsys):
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported  # ensure attribute exists on utils
    import utils
    import sys, types
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.parse_a2s_info = lambda data: None  # no details

    def fake_a2s(host, port, timeout=2.0):
        return b"\xff\xff\xff\xff\x49"  # minimal valid-looking response

    fake_q.a2s_info = fake_a2s
    fake_q.tcp_ping = None
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.query()

    assert "A2S" in capsys.readouterr().out


def test_query_falls_back_to_tcp_when_a2s_fails(monkeypatch, capsys):
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported  # ensure attribute exists on utils
    import utils
    import sys, types
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError

    def fake_a2s(host, port, timeout=2.0):
        raise OSError("no udp")

    def fake_tcp(host, port, timeout=2.0):
        return 3.14

    fake_q.a2s_info = fake_a2s
    fake_q.tcp_ping = fake_tcp
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.query()

    assert "TCP" in capsys.readouterr().out


def test_query_raises_server_error_when_both_fail(monkeypatch):
    srv = make_server(data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported  # ensure attribute exists on utils
    import utils
    import sys, types
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError

    fake_q.a2s_info = lambda host, port, timeout=2.0: (_ for _ in ()).throw(OSError("udp"))
    fake_q.tcp_ping = lambda host, port, timeout=2.0: (_ for _ in ()).throw(OSError("tcp"))
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    with pytest.raises(server_module.ServerError, match="not appear to be responding"):
        srv.query()


def test_query_uses_module_get_query_address(monkeypatch, capsys):
    calls = []
    module = DummyModule()
    module.get_query_address = lambda server: ("10.0.0.1", 27016, "tcp")

    srv = make_server(module=module, data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported  # ensure attribute exists on utils
    import utils
    import sys, types
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError

    def fake_tcp(host, port, timeout=2.0):
        calls.append((host, port))
        return 1.0

    fake_q.tcp_ping = fake_tcp
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.query()

    assert ("10.0.0.1", 27016) in calls


def test_query_uses_module_namespace_get_query_address(monkeypatch, capsys):
    calls = []
    module = DummyModule()
    module.MODULE = SimpleNamespace(
        get_query_address=lambda server: ("10.0.0.2", 27017, "tcp")
    )

    srv = make_server(module=module, data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError

    def fake_tcp(host, port, timeout=2.0):
        calls.append((host, port))
        return 1.0

    fake_q.tcp_ping = fake_tcp
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.query()

    assert calls == [("10.0.0.2", 27017)]


def test_query_uses_explicit_udp_protocol(monkeypatch, capsys):
    module = DummyModule()
    module.get_query_address = lambda server: ("10.0.0.1", 27016, "udp")

    srv = make_server(module=module, data=DummyData({"dir": "/srv/game", "port": "27015"}))

    import utils.query as _ensure_imported
    import utils
    import sys, types
    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.udp_ping = lambda host, port, timeout=2.0: 1.5
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.query()

    assert "UDP ping" in capsys.readouterr().out


def test_query_retries_a2s_after_wake_hook(monkeypatch, capsys):
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    wake_calls = []
    attempts = []
    module = DummyModule()
    module.wake_a2s_query = lambda server: wake_calls.append(server.name) or 0
    srv = make_server(module=module, data=DummyData({"port": 27015}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError

    def fake_a2s(host, port, timeout=2.0, phase2_timeout=None):
        attempts.append((host, port, timeout, phase2_timeout))
        if len(attempts) == 1:
            raise OSError("udp")
        return b"\xff\xff\xff\xff\x49stub"

    fake_q.a2s_info = fake_a2s
    fake_q.parse_a2s_info = lambda data: {
        "name": "Wake Test",
        "map": "cp_dustbowl",
        "game": "TF2",
        "players": 0,
        "max_players": 24,
    }

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(server_module.time, "sleep", lambda *_args: None)

    srv.query()

    assert wake_calls == ["alpha", "alpha"]
    assert attempts == [
        ("127.0.0.1", 27015, 15.0, 120.0),
        ("127.0.0.1", 27015, 15.0, 120.0),
    ]
    assert "Wake Test" in capsys.readouterr().out


# info
# ---------------------------------------------------------------------------


def test_info_succeeds_via_slp(monkeypatch, capsys):
    """info() uses slp_info when module returns protocol='slp'."""
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    srv = make_server(data=DummyData({"port": 25565, "module": "minecraft.vanilla"}))

    slp_data = {
        "description": "A test server",
        "players_online": 2,
        "players_max": 10,
        "version": "1.20.4",
        "player_names": ["Alice", "Bob"],
    }

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.slp_info = lambda host, port, timeout=5.0: slp_data

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(srv.module, "get_info_address",
                        lambda s: ("127.0.0.1", 25565, "slp"), raising=False)

    srv.info()

    out = capsys.readouterr().out
    assert "Server info (SLP" in out
    assert "Players" in out
    assert "2/10" in out


def test_info_succeeds_via_a2s(monkeypatch, capsys):
    """info() parses A2S_INFO when protocol='a2s'."""
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    srv = make_server(data=DummyData({"port": 27015, "module": "teamfortress2"}))

    a2s_parsed = {
        "name": "My TF2 Server",
        "map": "cp_badlands",
        "folder": "tf",
        "game": "Team Fortress",
        "appid": 440,
        "players": 4,
        "max_players": 24,
        "bots": 0,
    }

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.a2s_info = lambda host, port, timeout=2.0: b"\xff\xff\xff\xff\x49stub"
    fake_q.parse_a2s_info = lambda data: a2s_parsed

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.info()

    out = capsys.readouterr().out
    assert "Server info (A2S" in out
    assert "cp_badlands" in out
    assert "4/24" in out


def test_info_falls_back_to_tcp(monkeypatch, capsys):
    """info() falls back to TCP when A2S fails."""
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    srv = make_server(data=DummyData({"port": 27015, "module": "teamfortress2"}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.a2s_info = lambda host, port, timeout=2.0: (_ for _ in ()).throw(OSError("udp"))
    fake_q.tcp_ping = lambda host, port, timeout=2.0: 5.4

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.info()

    out = capsys.readouterr().out
    assert "Server port is open" in out


def test_run_command_dispatches_info(monkeypatch, capsys):
    """run_command('info') must reach Server.info(), not silently do nothing."""
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    srv = make_server(data=DummyData({"port": 25565, "module": "minecraft.vanilla"}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.slp_info = lambda host, port, timeout=5.0: {
        "description": "Test",
        "players_online": 0,
        "players_max": 20,
        "version": "1.20",
    }

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(srv.module, "get_info_address",
                        lambda s: ("127.0.0.1", 25565, "slp"), raising=False)

    srv.run_command("info")

    out = capsys.readouterr().out
    assert "Server info (SLP" in out


def test_info_json_output(monkeypatch, capsys):
    """info(as_json=True) emits a valid JSON object instead of human-readable text."""
    import json as _json
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    srv = make_server(data=DummyData({"port": 25565, "module": "minecraft.vanilla"}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.slp_info = lambda host, port, timeout=5.0: {
        "description": "A test server",
        "players_online": 3,
        "players_max": 20,
        "version": "1.20.4",
    }

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(srv.module, "get_info_address",
                        lambda s: ("127.0.0.1", 25565, "slp"), raising=False)

    srv.info(as_json=True)

    out = capsys.readouterr().out.strip()
    data = _json.loads(out)
    assert data["protocol"] == "slp"
    assert data["port"] == 25565
    assert data["players_online"] == 3
    assert data["players_max"] == 20
    assert "Server info" not in out


def test_info_uses_explicit_udp_protocol(monkeypatch, capsys):
    import json as _json
    import utils.query as _ensure_imported
    import utils
    import sys, types

    module = DummyModule()
    module.get_info_address = lambda server: ("127.0.0.1", 7777, "udp")
    srv = make_server(module=module, data=DummyData({"port": 7777}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.udp_ping = lambda host, port, timeout=2.0: 4.2
    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.info(as_json=True)

    data = _json.loads(capsys.readouterr().out.strip())
    assert data["protocol"] == "udp"
    assert data["port"] == 7777


def test_info_uses_module_namespace_wake_hook(monkeypatch, capsys):
    import json as _json
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    wake_calls = []
    module = DummyModule()
    module.MODULE = SimpleNamespace(
        wake_a2s_query=lambda server: wake_calls.append(server.name) or 0
    )
    srv = make_server(module=module, data=DummyData({"port": 27015}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    fake_q.a2s_calls = []

    def fake_a2s(host, port, timeout=2.0, phase2_timeout=None):
        fake_q.a2s_calls.append((host, port, timeout, phase2_timeout))
        return b"\xff\xff\xff\xff\x49stub"

    fake_q.a2s_info = fake_a2s
    fake_q.parse_a2s_info = lambda data: {
        "name": "My TF2 Server",
        "map": "cp_badlands",
        "folder": "tf",
        "game": "Team Fortress",
        "appid": 440,
        "players": 0,
        "max_players": 24,
        "bots": 0,
    }

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(server_module.time, "sleep", lambda *_args: None)

    srv.info(as_json=True)

    data = _json.loads(capsys.readouterr().out.strip())
    assert wake_calls == ["alpha"]
    assert fake_q.a2s_calls == [("127.0.0.1", 27015, 15.0, 120.0)]
    assert data["protocol"] == "a2s"


def test_info_uses_console_hook_for_hibernating_server(monkeypatch, capsys):
    import json as _json
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    module = DummyModule()
    module.get_hibernating_console_info = lambda server: {
        "name": "Hibernate TF2",
        "map": "cp_dustbowl",
        "version": "10515055/24 10515055 secure",
        "players": 0,
        "max_players": 16,
        "bots": 0,
    }
    srv = make_server(module=module, data=DummyData({"port": 27015}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    a2s_calls = []

    def fake_a2s_info(*args, **kwargs):
        a2s_calls.append((args, kwargs))
        raise OSError("A2S not available while idle")

    fake_q.a2s_info = fake_a2s_info

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.info(as_json=True)

    data = _json.loads(capsys.readouterr().out.strip())
    assert len(a2s_calls) == 1
    assert data["protocol"] == "console"
    assert data["name"] == "Hibernate TF2"
    assert data["map"] == "cp_dustbowl"


def test_info_uses_module_namespace_console_hook_for_hibernating_server(
    monkeypatch, capsys
):
    import json as _json
    import utils.query as _ensure_imported  # noqa: F401
    import utils
    import sys, types

    module = DummyModule()
    module.MODULE = SimpleNamespace(
        get_info_address=lambda server: ("10.0.0.5", 27015, "a2s"),
        get_hibernating_console_info=lambda server: {
            "name": "Hibernate CSS",
            "map": "de_dust2",
            "version": "6630498 secure",
            "players": 0,
            "max_players": 16,
            "bots": 0,
        },
    )
    srv = make_server(module=module, data=DummyData({"port": 27015}))

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = OSError
    a2s_calls = []

    def fake_a2s_info(*args, **kwargs):
        a2s_calls.append((args, kwargs))
        raise OSError("A2S not available while idle")

    fake_q.a2s_info = fake_a2s_info

    monkeypatch.setattr(utils, "query", fake_q)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    srv.info(as_json=True)

    data = _json.loads(capsys.readouterr().out.strip())
    assert len(a2s_calls) == 1
    assert data["protocol"] == "console"
    assert data["port"] == 27015
    assert data["name"] == "Hibernate CSS"
