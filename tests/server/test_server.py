from types import SimpleNamespace

import pytest

import server.server as server_module


class DummyData(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved = 0

    def save(self):
        self.saved += 1

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
    alias_module = SimpleNamespace(__file__="/tmp/alias.py", ALIAS_TARGET="real")
    real_module = SimpleNamespace(__file__="/tmp/real.py")
    imports = []

    def fake_import(name):
        imports.append(name)
        if name.endswith(".alias"):
            return alias_module
        if name.endswith(".real"):
            return real_module
        raise ImportError("missing")

    monkeypatch.setattr(server_module, "import_module", fake_import)
    monkeypatch.setattr(server_module, "SERVERMODULEPACKAGE", "gamemodules.")

    resolved_name, resolved_module = server_module._findmodule("alias")

    assert resolved_name == "real"
    assert resolved_module is real_module
    assert imports == ["gamemodules.alias", "gamemodules.real"]


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


def test_get_commands_args_and_descriptions_merge_module_data():
    srv = make_server()

    commands = srv.get_commands()
    description = srv.get_command_description("setup")

    assert "custom" in commands
    assert "extra setup details" in description
    assert srv.get_command_args("custom") == "custom-args"


def test_run_command_dispatches_builtin_and_custom_methods(monkeypatch):
    srv = make_server()
    calls = []
    monkeypatch.setattr(srv, "setup", lambda *args, **kwargs: calls.append(("setup", args, kwargs)))
    monkeypatch.setattr(srv, "connect", lambda *args, **kwargs: calls.append(("connect", args, kwargs)))
    monkeypatch.setattr(srv, "dump", lambda *args, **kwargs: calls.append(("dump", args, kwargs)))
    monkeypatch.setattr(srv, "doset", lambda *args, **kwargs: calls.append(("set", args, kwargs)))
    srv.module.command_functions = {"custom": lambda server, *args, **kwargs: calls.append(("custom", args, kwargs))}

    srv.run_command("setup", 1, flag=True)
    srv.run_command("message", "hello")
    srv.run_command("backup", "nightly")
    srv.run_command("connect")
    srv.run_command("dump")
    srv.run_command("set", "path", "value")
    srv.run_command("custom", 9)

    assert ("setup", (1,), {"flag": True}) in calls
    assert ("custom", (9,), {}) in calls
    assert ("set", ("path", "value"), {}) in calls
    assert ("message", (("hello",), {})) not in calls
    assert any(call[0] == "connect" for call in calls)
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
    assert srv.module.calls[1] == ("install", ("configured",), {"flag": True})


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


def test_doset_updates_nested_data_and_saves():
    srv = make_server(data=DummyData({"existing": {"items": []}}))

    srv.doset("existing.items.APPEND", "new")

    assert srv.data["existing"]["items"] == ["value"]
    assert srv.data.saved == 1


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
