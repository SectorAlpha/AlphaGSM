from io import StringIO
from types import SimpleNamespace

import pytest

import core.main as main_module


class FakeStdout:
    encoding = "utf-8"


class FakeProc:
    def __init__(self, output, returncode):
        self._output = output
        self.returncode = returncode

    def communicate(self):
        return self._output, b""


def test_split_server_name_supports_local_and_remote_names():
    assert main_module.split_server_name("alpha") == (None, "alpha")
    assert main_module.split_server_name("bob/alpha") == ("bob", "alpha")


def test_split_server_name_rejects_multiple_separators():
    with pytest.raises(main_module.ServerError, match="Only one / allowed"):
        main_module.split_server_name("a/b/c")


def test_get_all_all_servers_reads_running_and_saved_lists(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main_module.screen, "list_all_screens", lambda: ["alice/one", "two"])

    stopped = main_module.get_all_all_servers("stop")
    started = main_module.get_all_all_servers("start")

    assert stopped == ["alice/one", "two"]
    assert started == ["alice/one", "two"]
    assert "Using servers for '*/*':" in capsys.readouterr().err


def test_get_all_user_servers_reads_json_filenames(monkeypatch, capsys):
    monkeypatch.setattr(main_module.servermodule, "DATAPATH", "/srv/conf")
    monkeypatch.setattr(main_module.os, "listdir", lambda path: ["one.json", "two.json", "ignore.txt"])

    result = main_module.get_all_user_servers()

    assert result == [(None, "one"), (None, "two")]
    assert "Using servers for '*': one two" in capsys.readouterr().err


def test_expand_server_star_handles_user_and_tag_wildcards(monkeypatch, capsys):
    monkeypatch.setattr(main_module, "get_all_all_servers", lambda cmd: ["alice/one", "two"])
    monkeypatch.setattr(main_module, "get_all_user_servers", lambda: [(None, "mine")])

    assert main_module.expand_server_star("*", "*", "status") == [("alice", "one"), (None, "two")]
    assert main_module.expand_server_star(None, "*", "status") == [(None, "mine")]
    assert main_module.expand_server_star(None, "one", "status") == [(None, "one")]
    assert main_module.expand_server_star("*", "one", "status") == ()
    assert "Can't specify a server but '*' user" in capsys.readouterr().out


def test_get_run_cmd_and_run_as_cmd_build_expected_subprocess_command(monkeypatch):
    monkeypatch.setattr(main_module.os.path, "dirname", lambda path: "/repo/core")
    monkeypatch.setattr(main_module.os.path, "abspath", lambda path: path)
    monkeypatch.setattr(main_module.os.path, "realpath", lambda path: path)

    local = main_module.get_run_cmd("alphagsm", "alpha", ["status"], multi=True)
    remote = main_module.get_run_as_cmd("alphagsm", "bob", "alpha", ["status"], multi=False)

    assert local == ["/repo/alphagsm-internal", "1", "alphagsm", "alpha", "status"]
    assert remote == ["sudo", "-Hu", "bob", "/repo/alphagsm-internal", "0", "alphagsm", "alpha", "status"]


def test_run_as_returns_subprocess_status(monkeypatch, capsys):
    monkeypatch.setattr(main_module, "get_run_as_cmd", lambda name, user, server, args: ["cmd"])
    monkeypatch.setattr(main_module.sp, "call", lambda cmd: 3)

    result = main_module.run_as("alphagsm", "bob", "alpha", ["status"])

    assert result == 3
    assert "Command finished with return status 3" in capsys.readouterr().err


def test_run_list_multi_prefixes_remote_output_and_combines_return_codes(monkeypatch, capsys):
    outputs = [
        FakeProc(b"one\n", 2),
        FakeProc(b"two\n", 4),
    ]
    monkeypatch.setattr(main_module, "stdout", FakeStdout())
    monkeypatch.setattr(main_module, "get_run_as_cmd", lambda *args, **kwargs: ["remote"])
    monkeypatch.setattr(main_module, "get_run_cmd", lambda *args, **kwargs: ["local"])
    monkeypatch.setattr(main_module.sp, "Popen", lambda cmd, stdout=None: outputs.pop(0))

    result = main_module.run_list_multi("alphagsm", [("bob", "alpha"), (None, "beta")], ["list"])

    captured = capsys.readouterr()
    assert result == 10
    assert "bob/one" in captured.out
    assert "two" in captured.out
    assert "Command finished with return status 2" in captured.err


def test_internal_is_running_matches_internal_marker():
    assert main_module._internal_is_running(b"#%AlphaGSM-INTERNAL%#\n") is True
    assert main_module._internal_is_running(b"other\n") is False


def test_run_multi_uses_multiplexer_and_combines_return_codes(monkeypatch):
    added = []

    class FakeMultiplexer:
        def processall(self):
            added.append("processed")

        def checkreturnvalues(self):
            return {"one": 0, "two": 2}

    monkeypatch.setattr(main_module.mp, "Multiplexer", FakeMultiplexer)
    monkeypatch.setattr(main_module.mp, "addtomultiafter", lambda multi, tag, fn, cmd, **kwargs: added.append((tag, cmd, kwargs)))
    monkeypatch.setattr(main_module, "get_run_as_cmd", lambda *args, **kwargs: ["remote"])
    monkeypatch.setattr(main_module, "get_run_cmd", lambda *args, **kwargs: ["local"])

    result = main_module.run_multi("alphagsm", 2, [("bob", "alpha"), (None, "beta")], ["status"])

    assert result == 2
    assert added[0][0] == "bob/alpha"
    assert added[1][0] == "beta"
    assert added[2] == "processed"


def test_run_one_handles_remote_list_and_remote_command(monkeypatch):
    monkeypatch.setattr(main_module, "run_list_multi", lambda name, servers, args: 7)
    monkeypatch.setattr(main_module, "run_as", lambda name, user, tag, args: 9)

    assert main_module.run_one("alphagsm", ("bob", "alpha"), "list", []) == 7
    assert main_module.run_one("alphagsm", ("bob", "alpha"), "status", []) == 9


def test_run_one_create_requires_type_and_restricts_followup(monkeypatch, capsys):
    monkeypatch.setattr(main_module, "help", lambda *args, **kwargs: None)

    assert main_module.run_one("alphagsm", (None, "alpha"), "create", []) == 2
    assert main_module.run_one("alphagsm", (None, "alpha"), "create", ["minecraft", "start"]) == 2
    assert "Type of server to create is a required argument" in capsys.readouterr().err


def test_run_one_parses_and_runs_local_command(monkeypatch):
    server = SimpleNamespace(
        get_command_args=lambda cmd: "spec",
        run_command=lambda cmd, *args, **opts: calls.append((cmd, args, opts)),
    )
    calls = []
    monkeypatch.setattr(main_module, "Server", lambda tag, *rest: server)
    monkeypatch.setattr(main_module.cmdparse, "parse", lambda args, spec: (["arg1"], {"flag": True}))

    result = main_module.run_one("alphagsm", (None, "alpha"), "status", ["raw"])

    assert result == 0
    assert calls == [("status", ("arg1",), {"flag": True})]
    assert main_module.program.PATH.endswith("alphagsm")


def test_run_one_returns_error_codes_for_parse_and_run_failures(monkeypatch):
    server = SimpleNamespace(get_command_args=lambda cmd: "spec")
    monkeypatch.setattr(main_module, "Server", lambda tag, *rest: server)
    monkeypatch.setattr(main_module, "help", lambda *args, **kwargs: None)

    monkeypatch.setattr(main_module.cmdparse, "parse", lambda args, spec: (_ for _ in ()).throw(main_module.cmdparse.OptionError("bad parse")))
    assert main_module.run_one("alphagsm", (None, "alpha"), "status", []) == 2

    monkeypatch.setattr(main_module.cmdparse, "parse", lambda args, spec: ([], {}))
    server.run_command = lambda cmd, *args, **kwargs: (_ for _ in ()).throw(main_module.ServerError("bad run"))
    assert main_module.run_one("alphagsm", (None, "alpha"), "status", []) == 1

    server.run_command = lambda cmd, *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    assert main_module.run_one("alphagsm", (None, "alpha"), "status", []) == 3


def test_main_handles_help_banned_names_and_multi_server_paths(monkeypatch):
    monkeypatch.setattr(main_module, "help", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "expand_server_star", lambda user, tag, cmd: [(user, tag)])
    monkeypatch.setattr(main_module, "run_one", lambda *args: 11)
    monkeypatch.setattr(main_module, "run_multi", lambda *args: 12)
    monkeypatch.setattr(main_module, "run_list_multi", lambda *args: 13)

    assert main_module.main("alphagsm", ["-h"]) == 0
    assert main_module.main("alphagsm", ["help", "status"]) == 2
    assert main_module.main("alphagsm", ["alpha"]) == 1
    assert main_module.main("alphagsm", ["2", "a", "b", "status"]) == 12
    assert main_module.main("alphagsm", ["2", "a", "b", "list"]) == 13
    assert main_module.main("alphagsm", ["alpha", "status"]) == 11


def test_print_handled_ex_uses_traceback_in_debug(monkeypatch):
    called = []
    monkeypatch.setattr(main_module, "DEBUG", True)
    monkeypatch.setattr(main_module.traceback, "print_exc", lambda: called.append(True))

    main_module.print_handled_ex(RuntimeError("boom"))

    assert called == [True]
