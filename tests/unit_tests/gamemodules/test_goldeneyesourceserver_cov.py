"""Focused lifecycle coverage for the GoldenEye: Source BYO module."""

import ast
import importlib.util
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


sys.modules.pop("gamemodules.goldeneyesourceserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.archive_install": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
    },
):
    import gamemodules.goldeneyesourceserver as mod
    from server import ServerError


REQUIRED_LAYOUT = (
    "srcds_run",
    "steam_appid.txt",
    "bin",
    "hl2",
    "gesource/gameinfo.txt",
    "gesource/maps/ge_archives.bsp",
)
INTEGRATION_TEST = Path("tests/integration_tests/test_goldeneyesourceserver.py")
GUIDE = Path("docs/servers/goldeneyesourceserver.md")
TEST_STATUS = Path("docs/TEST_STATUS.md")
BYO_REGISTRY = Path("enabled_byo_servers.conf")


def _configure_server(tmp_path):
    server = DummyServer("goldeneye")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    return server


def _stage_complete_tree(tmp_path, *, missing=None, executable=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    for relative_path in REQUIRED_LAYOUT:
        if relative_path == missing:
            continue
        path = tmp_path / relative_path
        if relative_path == "steam_appid.txt":
            path.write_text("310\n", encoding="utf-8")
        elif path.suffix or relative_path == "srcds_run":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\n", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)
    if executable and missing != "srcds_run":
        os.chmod(tmp_path / "srcds_run", 0o755)


def test_setup_surface_is_staged_tree_only():
    assert mod.command_args["setup"].options == ()


def test_configure_without_override_never_resolves_a_network_download(tmp_path):
    server = DummyServer()

    with patch(
        "urllib.request.urlopen",
        side_effect=AssertionError("configure attempted a network request"),
    ):
        mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert "url" not in server.data
    assert "download_name" not in server.data
    assert server.data["source_app_id"] == 310
    assert server.data["artifact_version"] == "5.0.6"


def test_provider_requirements_declare_complete_operator_staged_assets():
    requirement = mod.get_provider_requirements(DummyServer())[0]
    actions = " ".join(requirement["actions"])

    assert requirement["provider"] == "operator"
    assert requirement["kind"] == "asset"
    assert requirement["support_category"] == "assets"
    assert requirement["required_for"] == ("setup", "start")
    assert "Source 2007/AppID 310" in requirement["summary"]
    assert "top-level gesource" in requirement["summary"]
    assert "required operator marker" in actions
    assert "does not authenticate asset provenance" in actions
    assert "Manually compare" in actions
    assert "AlphaGSM does not verify the artifact" in actions


def test_release_evidence_is_pinned():
    assert mod.SOURCE_2007_APP_ID == 310
    assert mod.GES_RELEASE_VERSION == "5.0.6"
    assert mod.GES_RELEASE_SHA256 == (
        "79643189e9d6549e13ed9545d2277cb34bac05fff645d44d9de1f0ab030610d3"
    )


@pytest.mark.parametrize("missing", REQUIRED_LAYOUT)
def test_install_rejects_incomplete_staged_tree_with_shared_byo_guidance(
    tmp_path, missing
):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path, missing=missing)

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\).+" + missing):
        mod.install(server)


def test_install_rejects_non_executable_source_launcher(tmp_path):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path, executable=False)

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\).+srcds_run.+executable"):
        mod.install(server)


@pytest.mark.parametrize("marker", ("440\n", " 310\n", "310\n\n"))
def test_install_rejects_accidental_source_appid_marker_mismatch(tmp_path, marker):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path)
    (tmp_path / "steam_appid.txt").write_text(marker, encoding="utf-8")

    with pytest.raises(ServerError, match=r"steam_appid.txt.+exactly 310"):
        mod.install(server)


def test_install_accepts_and_persists_complete_staged_tree(tmp_path):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path)
    saves_before_install = server.data.saved

    mod.install(server)

    assert server.data.saved == saves_before_install + 1
    assert "url" not in server.data
    assert "current_url" not in server.data


def test_get_start_command_validates_layout_and_builds_source_argv(tmp_path):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path)

    command, working_dir = mod.get_start_command(server)

    assert command == [
        "./srcds_run",
        "-game",
        "gesource",
        "+map",
        "ge_archives",
        "+maxplayers",
        "16",
        "-port",
        "27015",
    ]
    assert working_dir == str(tmp_path) + "/"


def test_get_start_command_rejects_incomplete_tree_with_byo_guidance(tmp_path):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path, missing="gesource/gameinfo.txt")

    with pytest.raises(ServerError, match=r"ENABLED \(BYO\).+gesource/gameinfo.txt"):
        mod.get_start_command(server)


def test_process_and_docker_start_commands_remain_in_parity(tmp_path):
    server = _configure_server(tmp_path)
    _stage_complete_tree(tmp_path)

    process_command, process_working_dir = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_working_dir = mod.get_start_command(server)
    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert docker_command == process_command
    assert docker_working_dir == process_working_dir
    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "tcp"},
    ]
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True


def _replace_with_symlink(path, target, *, relative):
    is_directory = path.is_dir()
    if is_directory:
        path.rmdir()
        target.mkdir(parents=True)
    else:
        path.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("#!/bin/sh\n", encoding="utf-8")
        if path.name == "srcds_run":
            os.chmod(target, 0o755)
        elif path.name == "steam_appid.txt":
            target.write_text("310\n", encoding="utf-8")
    link_target = os.path.relpath(target, path.parent) if relative else str(target)
    path.symlink_to(link_target, target_is_directory=is_directory)


def _start_for_runtime(server, runtime):
    if runtime == "process":
        return mod.get_start_command(server)
    server.data["runtime"] = "docker"
    return mod.get_container_spec(server)


def _create_non_marker_path(install_dir, kind):
    relative_path = "optional/assets" if kind == "directory" else "optional/addon.dat"
    candidate = install_dir / relative_path
    if kind == "directory":
        candidate.mkdir(parents=True)
    else:
        candidate.parent.mkdir(parents=True)
        candidate.write_text("optional content\n", encoding="utf-8")
    return relative_path, candidate


@pytest.mark.parametrize("runtime", ("process", "docker"))
@pytest.mark.parametrize("relative_path", REQUIRED_LAYOUT)
def test_process_and_docker_reject_external_required_path_symlinks(
    tmp_path, runtime, relative_path
):
    install_dir = tmp_path / "server"
    outside_dir = tmp_path / "outside"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    candidate = install_dir / relative_path
    external_target = outside_dir / relative_path
    _replace_with_symlink(candidate, external_target, relative=True)

    with pytest.raises(ServerError, match=r"outside the install root"):
        _start_for_runtime(server, runtime)


@pytest.mark.parametrize("runtime", ("process", "docker"))
def test_process_and_docker_allow_internal_relative_required_path_symlinks(
    tmp_path, runtime
):
    install_dir = tmp_path / "server"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    for relative_path in REQUIRED_LAYOUT:
        candidate = install_dir / relative_path
        internal_target = install_dir / "payload" / relative_path
        _replace_with_symlink(candidate, internal_target, relative=True)

    result = _start_for_runtime(server, runtime)

    if runtime == "process":
        assert result[0][0] == "./srcds_run"
    else:
        assert result["command"][0] == "./srcds_run"
        assert result["working_dir"] == "/srv/server"


@pytest.mark.parametrize("runtime", ("process", "docker"))
@pytest.mark.parametrize("relative_path", REQUIRED_LAYOUT)
def test_process_and_docker_reject_absolute_internal_symlink(
    tmp_path, runtime, relative_path
):
    install_dir = tmp_path / "server"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    _replace_with_symlink(
        install_dir / relative_path,
        install_dir / "payload" / relative_path,
        relative=False,
    )

    with pytest.raises(ServerError, match=r"absolute symlink.+Docker"):
        _start_for_runtime(server, runtime)


@pytest.mark.parametrize("runtime", ("process", "docker"))
@pytest.mark.parametrize("relative_path", REQUIRED_LAYOUT)
def test_process_and_docker_reject_symlink_escape_then_reentry(
    tmp_path, runtime, relative_path
):
    install_dir = tmp_path / "server"
    outside_dir = tmp_path / "outside"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    outside_dir.mkdir()

    candidate = install_dir / relative_path
    internal_target = install_dir / "payload" / relative_path
    _replace_with_symlink(candidate, internal_target, relative=True)
    candidate.unlink()
    escaping_target = os.path.join(
        os.path.relpath(outside_dir, candidate.parent),
        os.path.relpath(internal_target, outside_dir),
    )
    candidate.symlink_to(
        escaping_target,
        target_is_directory=internal_target.is_dir(),
    )
    assert candidate.resolve(strict=True) == internal_target.resolve(strict=True)

    with pytest.raises(ServerError, match=r"leaves the install root"):
        _start_for_runtime(server, runtime)


@pytest.mark.parametrize("runtime", ("process", "docker"))
def test_process_and_docker_allow_nested_internal_relative_symlink_chains(
    tmp_path, runtime
):
    install_dir = tmp_path / "server"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    for relative_path in REQUIRED_LAYOUT:
        candidate = install_dir / relative_path
        intermediate = install_dir / "links" / relative_path
        internal_target = install_dir / "payload" / relative_path
        _replace_with_symlink(candidate, intermediate, relative=True)
        _replace_with_symlink(intermediate, internal_target, relative=True)

    result = _start_for_runtime(server, runtime)

    if runtime == "process":
        assert result[0][0] == "./srcds_run"
    else:
        assert result["command"][0] == "./srcds_run"
        assert result["working_dir"] == "/srv/server"


@pytest.mark.parametrize("runtime", ("process", "docker"))
@pytest.mark.parametrize("relative_path", REQUIRED_LAYOUT)
def test_process_and_docker_reject_required_path_symlink_cycles(
    tmp_path, runtime, relative_path
):
    install_dir = tmp_path / "server"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)

    candidate = install_dir / relative_path
    cycle_peer = install_dir / "cycles" / relative_path
    _replace_with_symlink(candidate, cycle_peer, relative=True)
    is_directory = cycle_peer.is_dir()
    if is_directory:
        cycle_peer.rmdir()
    else:
        cycle_peer.unlink()
    cycle_peer.symlink_to(
        os.path.relpath(candidate, cycle_peer.parent),
        target_is_directory=is_directory,
    )

    with pytest.raises(ServerError, match=r"symlink cycle"):
        _start_for_runtime(server, runtime)


@pytest.mark.parametrize("runtime", ("process", "docker"))
@pytest.mark.parametrize("kind", ("file", "directory"))
@pytest.mark.parametrize(
    ("scenario", "error_match"),
    (
        ("absolute", r"absolute symlink"),
        ("external", r"outside the install root"),
        ("escape-reentry", r"leaves the install root"),
        ("cycle", r"symlink cycle"),
    ),
)
def test_process_and_docker_reject_unsafe_non_marker_tree_symlinks(
    tmp_path, runtime, kind, scenario, error_match
):
    install_dir = tmp_path / "server"
    outside_dir = tmp_path / "outside"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    relative_path, candidate = _create_non_marker_path(install_dir, kind)
    internal_target = install_dir / "payload" / relative_path

    if scenario == "absolute":
        _replace_with_symlink(candidate, internal_target, relative=False)
    elif scenario == "external":
        _replace_with_symlink(
            candidate,
            outside_dir / relative_path,
            relative=True,
        )
    elif scenario == "escape-reentry":
        outside_dir.mkdir()
        _replace_with_symlink(candidate, internal_target, relative=True)
        candidate.unlink()
        candidate.symlink_to(
            os.path.join(
                os.path.relpath(outside_dir, candidate.parent),
                os.path.relpath(internal_target, outside_dir),
            ),
            target_is_directory=internal_target.is_dir(),
        )
        assert candidate.resolve(strict=True) == internal_target.resolve(strict=True)
    else:
        cycle_peer = install_dir / "cycles" / relative_path
        _replace_with_symlink(candidate, cycle_peer, relative=True)
        is_directory = cycle_peer.is_dir()
        if is_directory:
            cycle_peer.rmdir()
        else:
            cycle_peer.unlink()
        cycle_peer.symlink_to(
            os.path.relpath(candidate, cycle_peer.parent),
            target_is_directory=is_directory,
        )

    with pytest.raises(ServerError, match=error_match):
        _start_for_runtime(server, runtime)


@pytest.mark.parametrize("runtime", ("process", "docker"))
def test_process_and_docker_allow_internal_non_marker_symlink_chains(
    tmp_path, runtime
):
    install_dir = tmp_path / "server"
    server = _configure_server(install_dir)
    _stage_complete_tree(install_dir)
    for kind in ("file", "directory"):
        relative_path, candidate = _create_non_marker_path(install_dir, kind)
        intermediate = install_dir / "links" / relative_path
        internal_target = install_dir / "payload" / relative_path
        _replace_with_symlink(candidate, intermediate, relative=True)
        _replace_with_symlink(intermediate, internal_target, relative=True)

    _start_for_runtime(server, runtime)


def _load_integration_helper(name, *, copytree=shutil.copytree):
    conftest_stub = ModuleType("conftest")
    for imported_name in (
        "assert_alphagsm_result_ok",
        "capture_alphagsm_stop",
        "require_integration_opt_in",
        "default_runtime_backend",
        "require_command_for_runtime",
        "pick_free_udp_port",
        "write_config",
        "alphagsm_env",
        "run_and_assert_ok",
        "run_alphagsm",
        "log_command_result",
        "skip_for_known_steamcmd_issue",
        "wait_for_runtime_log_marker",
        "wait_for_udp_closed",
    ):
        setattr(conftest_stub, imported_name, MagicMock(name=imported_name))

    spec = importlib.util.spec_from_file_location(
        "_goldeneyesourceserver_integration_contract",
        INTEGRATION_TEST,
    )
    assert spec is not None
    assert spec.loader is not None
    integration_module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", {"conftest": conftest_stub}):
        spec.loader.exec_module(integration_module)
    integration_module.shutil = SimpleNamespace(copytree=copytree)
    return getattr(integration_module, name)


@pytest.mark.parametrize("source_kind", ("missing", "file"))
def test_explicit_staged_tree_path_failures_are_path_neutral(tmp_path, source_kind):
    secret_source = tmp_path / "TOKEN_super-secret-owned-tree"
    if source_kind == "file":
        secret_source.write_text("not a directory\n", encoding="utf-8")
    stage_tree = _load_integration_helper("_stage_explicit_tree")

    with pytest.raises(pytest.fail.Exception) as exc_info:
        stage_tree(str(secret_source), tmp_path / "server")

    assert str(secret_source) not in str(exc_info.value)
    assert "super-secret-owned-tree" not in str(exc_info.value)


def test_explicit_staged_tree_copy_failures_are_path_neutral(tmp_path):
    secret_source = tmp_path / "TOKEN_super-secret-owned-tree"
    secret_source.mkdir()
    copytree = MagicMock(side_effect=OSError("copy failed: " + str(secret_source)))
    stage_tree = _load_integration_helper("_stage_explicit_tree", copytree=copytree)

    with pytest.raises(pytest.fail.Exception) as exc_info:
        stage_tree(str(secret_source), tmp_path / "server")

    assert str(secret_source) not in str(exc_info.value)
    assert "super-secret-owned-tree" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("helper_name", "payload"),
    (
        (
            "_assert_query_semantics",
            "InviteCode=invite-super-secret password=query-super-secret",
        ),
        (
            "_assert_info_semantics",
            "InviteCode=invite-super-secret password=info-super-secret",
        ),
        (
            "_assert_info_json_semantics",
            {
                "protocol": "InviteCode=invite-super-secret",
                "players": "password=json-super-secret",
            },
        ),
    ),
)
def test_explicit_tree_semantic_failures_do_not_expose_payload_secrets(
    helper_name, payload
):
    helper = _load_integration_helper(helper_name)

    with pytest.raises(AssertionError) as exc_info:
        helper(payload)

    message = str(exc_info.value)
    assert "invite-super-secret" not in message
    assert "query-super-secret" not in message
    assert "info-super-secret" not in message
    assert "json-super-secret" not in message


def test_integration_uses_explicit_staged_tree_and_shared_byo_gate():
    text = INTEGRATION_TEST.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lifecycle = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "test_goldeneyesourceserver_lifecycle"
    )
    main_try = next(node for node in lifecycle.body if isinstance(node, ast.Try))
    try_index = lifecycle.body.index(main_try)
    start_call = "_run_asserted_lifecycle_command(env, server_name, 'start')"
    asserted_helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_run_asserted_lifecycle_command"
    )
    asserted_helper_text = ast.unparse(asserted_helper)
    skip_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "skip_for_known_steamcmd_issue"
    ]
    skip_if = next(
        statement
        for statement in lifecycle.body
        if isinstance(statement, ast.If)
        and any(call in list(ast.walk(statement)) for call in skip_calls)
    )

    assert "ALPHAGSM_GOLDENEYE_SOURCE_SERVER_DIR" in text
    assert "shutil.copytree" in text
    assert "run_alphagsm" in asserted_helper_text
    assert "log_command_result" in asserted_helper_text
    assert "assert_alphagsm_result_ok" in asserted_helper_text
    assert "skip_for_known_steamcmd_issue" not in asserted_helper_text
    assert len(skip_calls) == 1
    assert isinstance(skip_if.test, ast.BoolOp)
    assert isinstance(skip_if.test.op, ast.And)
    assert {ast.unparse(condition) for condition in skip_if.test.values} == {
        "result.returncode != 0",
        "not staged_tree",
    }
    assert any(
        ast.unparse(statement) == "assert_alphagsm_result_ok(result)"
        for statement in lifecycle.body[:try_index]
    )
    assert ast.unparse(main_try.body[0]) == start_call
    lifecycle_try_text = ast.unparse(main_try)
    assert "run_and_assert_ok" not in lifecycle_try_text
    for command_call in (
        "_run_asserted_lifecycle_command(env, server_name, 'start')",
        "_run_asserted_lifecycle_command(env, server_name, 'status')",
        "_run_asserted_lifecycle_command(env, server_name, 'query')",
        "_run_asserted_lifecycle_command(env, server_name, 'info')",
        "_run_asserted_lifecycle_command(env, server_name, 'info', '--json')",
    ):
        assert command_call in lifecycle_try_text
    assert "_assert_query_semantics(query_result.stdout)" in lifecycle_try_text
    assert "_assert_info_semantics(info_result.stdout)" in lifecycle_try_text
    assert "_assert_info_json_semantics(_info_data)" in lifecycle_try_text
    assert "query_result.stdout!r" not in text
    assert "_info_data!r" not in text
    assert not any(
        start_call in ast.unparse(statement)
        for statement in lifecycle.body[:try_index]
    )
    assert main_try.handlers == []
    assert main_try.orelse == []
    assert len(main_try.finalbody) == 1
    assert ast.unparse(main_try.finalbody[0]) == (
        "stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])"
    )
    assert ast.unparse(lifecycle.body[try_index + 1]) == (
        "assert_alphagsm_result_ok(stop_result)"
    )
    assert "assert result.returncode" not in text
    assert "assert stop_result.returncode" not in text
    assert "pytest.mark.skip" not in text
    assert '"-u"' not in text


def test_public_support_surfaces_classify_goldeneye_as_assets_byo():
    registry = BYO_REGISTRY.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    normalized_guide = " ".join(guide.split())
    tracker = TEST_STATUS.read_text(encoding="utf-8")
    passed_section, remainder = tracker.split("## ENABLED (AUTH)", 1)
    byo_section = remainder.split("## ENABLED (BYO)", 1)[1].split("## DISABLED", 1)[0]

    assert "goldeneyesourceserver\tassets\t" in registry
    assert "Source 2007/AppID 310" in registry
    assert "`ENABLED (BYO)`" in guide
    assert "241-byte HTML meta-refresh" in guide
    assert "steam_appid.txt" in guide
    assert "accidental AppID mismatch guard" in normalized_guide
    assert "does not authenticate asset provenance" in normalized_guide
    assert "Manually compare" in normalized_guide
    assert "AlphaGSM does not verify the artifact" in normalized_guide
    assert "prevents an unrelated Source installation" not in guide
    assert "| goldeneyesourceserver |" not in passed_section
    assert "| goldeneyesourceserver |" in byo_section
    assert "Source 2007/AppID 310" in byo_section


def test_do_stop_uses_runtime_console(monkeypatch):
    send_to_server = MagicMock()
    monkeypatch.setattr(mod.runtime_module, "send_to_server", send_to_server)
    server = DummyServer()

    mod.do_stop(server, 0)

    send_to_server.assert_called_once_with(server, "\003")


def test_status_handles_unavailable_info(capsys):
    server = DummyServer()

    mod.status(server, verbose=True)

    assert "Status check failed" in capsys.readouterr().out


def test_message_uses_shared_unsupported_notice(capsys):
    mod.message(DummyServer(), "hello")

    assert "doesn't support generic messages" in capsys.readouterr().out


def test_backup_delegates_to_shared_backup_helper(monkeypatch):
    backup = MagicMock()
    monkeypatch.setattr(mod.gamemodule_common, "run_backup", backup)
    server = DummyServer()

    mod.backup(server, "default")

    backup.assert_called_once_with(
        server,
        "default",
        backup_module=mod.backup_utils,
    )


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    (
        (("port",), "27016", 27016),
        (("maxplayers",), "24", 24),
        (("exe_name",), "srcds_run", "srcds_run"),
        (("dir",), "/srv/goldeneye", "/srv/goldeneye"),
        (("game",), "gesource", "gesource"),
        (("startmap",), "ge_archives", "ge_archives"),
    ),
)
def test_checkvalue_accepts_supported_values(key, value, expected):
    assert mod.checkvalue(DummyServer(), key, value) == expected


def test_checkvalue_rejects_retired_download_keys():
    with pytest.raises(ServerError, match="Unsupported key"):
        mod.checkvalue(DummyServer(), ("url",), "https://example.invalid/archive")


def test_checkvalue_rejects_missing_or_unknown_values():
    with pytest.raises(ServerError):
        mod.checkvalue(DummyServer(), ())
    with pytest.raises(ServerError):
        mod.checkvalue(DummyServer(), ("port",))
    with pytest.raises(ServerError):
        mod.checkvalue(DummyServer(), ("unknown",), "value")
