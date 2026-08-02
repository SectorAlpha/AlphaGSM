"""Unit tests for integration-test helper behaviour."""

import ast
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest
from utils.simple_kv_config import rewrite_space_config


def _retaining_clock(*values):
    """Return successive clock values, retaining the final value thereafter."""

    remaining = iter(values)
    final_value = values[-1]
    return lambda: next(remaining, final_value)


def _owned_traceback_locals(exception, *function_names):
    """Return local-variable representations from selected helper frames."""

    frames = []
    traceback = exception.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_name in function_names:
            frames.append(repr(frame.f_locals))
        traceback = traceback.tb_next
    return "\n".join(frames)


def _function_node(source, function_name):
    module = ast.parse(source)
    matches = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    return matches[0] if len(matches) == 1 else None


def _is_named_call(node, function_name):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == function_name
    )


def _uses_shared_readiness_failure(source, function_name):
    function = _function_node(source, function_name)
    return function is not None and any(
        _is_named_call(node, "fail_readiness_timeout")
        for node in ast.walk(function)
    )


def _a2s_tcp_probe_is_diagnostic(source):
    function = _function_node(source, "wait_for_a2s_ready")
    if function is None:
        return False
    direct_socket_calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "socket"
        and node.func.attr == "create_connection"
    ]
    failure_calls = [
        node
        for node in ast.walk(function)
        if _is_named_call(node, "fail_readiness_timeout")
    ]
    if direct_socket_calls or len(failure_calls) != 1:
        return False
    diagnostics_keyword = next(
        (keyword.value for keyword in failure_calls[0].keywords if keyword.arg == "diagnostics"),
        None,
    )
    passes_diagnostics = (
        isinstance(diagnostics_keyword, ast.Call)
        and isinstance(diagnostics_keyword.func, ast.Name)
        and diagnostics_keyword.func.id == "tuple"
        and len(diagnostics_keyword.args) == 1
        and isinstance(diagnostics_keyword.args[0], ast.Name)
        and diagnostics_keyword.args[0].id == "diagnostics"
    )
    diagnostic_assignments = [
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "diagnostics"
            for target in node.targets
        )
    ]
    if not passes_diagnostics or len(diagnostic_assignments) != 1:
        return False
    diagnostics = diagnostic_assignments[0]
    has_label = any(
        isinstance(node, ast.Constant) and node.value == "A2S TCP probe"
        for node in ast.walk(diagnostics)
    )
    has_probe_call = any(
        _is_named_call(node, "_dump_a2s_tcp_probe")
        for node in ast.walk(diagnostics)
    )
    return has_label and has_probe_call


def _is_sys_exc_info_value(node):
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == 1
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "sys"
        and node.value.func.attr == "exc_info"
    )


def _direct_assignment_call(statement, target_name, function_name):
    if (
        not isinstance(statement, ast.Assign)
        or len(statement.targets) != 1
        or not isinstance(statement.targets[0], ast.Name)
        or statement.targets[0].id != target_name
        or not _is_named_call(statement.value, function_name)
    ):
        return None
    return statement.value


def _lifecycle_try(function):
    candidates = []
    for index, statement in enumerate(function.body):
        if (
            not isinstance(statement, ast.Try)
            or statement.handlers
            or statement.orelse
            or len(statement.finalbody) != 1
        ):
            continue
        cleanup_call = _direct_assignment_call(
            statement.finalbody[0],
            "stop_result",
            "capture_alphagsm_stop",
        )
        if cleanup_call is None:
            continue
        if (
            len(cleanup_call.args) != 3
            or not isinstance(cleanup_call.args[0], ast.Name)
            or cleanup_call.args[0].id != "env"
            or not isinstance(cleanup_call.args[1], ast.Name)
            or cleanup_call.args[1].id != "server_name"
            or not _is_sys_exc_info_value(cleanup_call.args[2])
        ):
            continue
        if any(
            isinstance(node, ast.Try) and node.handlers
            for body_statement in statement.body
            for node in ast.walk(body_statement)
        ):
            continue
        if any(
            isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom))
            for body_statement in statement.body
            for node in ast.walk(body_statement)
        ):
            continue
        candidates.append((index, statement))
    return candidates[0] if len(candidates) == 1 else None


def _is_direct_stop_assertion(statement):
    return (
        isinstance(statement, ast.Expr)
        and _is_named_call(statement.value, "assert_alphagsm_result_ok")
        and len(statement.value.args) == 1
        and isinstance(statement.value.args[0], ast.Name)
        and statement.value.args[0].id == "stop_result"
    )


def _lifecycle_cleanup_contract(source, function_name):
    function = _function_node(source, function_name)
    if function is None:
        return False
    lifecycle_try = _lifecycle_try(function)
    if lifecycle_try is None:
        return False
    cleanup_try_index, _ = lifecycle_try
    assertion_index = cleanup_try_index + 1
    return (
        assertion_index < len(function.body)
        and _is_direct_stop_assertion(function.body[assertion_index])
    )


def _game_lifecycle_contract(source, function_name, game):
    try:
        module = ast.parse(source)
    except SyntaxError:
        return False
    matches = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    function = matches[0] if len(matches) == 1 else None
    if function is None or not _lifecycle_cleanup_contract(source, function_name):
        return False

    trusted_names = {
        "capture_alphagsm_stop",
        "pytest",
        "run_and_assert_ok",
        "wait_for_udp_closed",
    }
    trusted_imports = {name: 0 for name in trusted_names}
    for statement in ast.walk(module):
        if isinstance(statement, ast.Import):
            for imported in statement.names:
                bound_name = imported.asname or imported.name.split(".", maxsplit=1)[0]
                if imported.name == "pytest":
                    if imported.asname is not None or statement not in module.body:
                        return False
                    trusted_imports["pytest"] += 1
                elif bound_name == "pytest":
                    return False
        elif isinstance(statement, ast.ImportFrom):
            if statement.module == "pytest":
                return False
            for imported in statement.names:
                bound_name = imported.asname or imported.name
                if imported.name in trusted_names:
                    if (
                        imported.name == "pytest"
                        or statement.module != "conftest"
                        or imported.asname is not None
                        or statement not in module.body
                    ):
                        return False
                    trusted_imports[imported.name] += 1
                elif bound_name in trusted_names:
                    return False
    if any(count != 1 for count in trusted_imports.values()):
        return False

    for node in ast.walk(module):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node.id in trusted_names
        ):
            return False
        if isinstance(node, ast.arg) and node.arg in trusted_names:
            return False
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name in trusted_names
        ):
            return False
        if (
            isinstance(node, (ast.Global, ast.Nonlocal))
            and trusted_names.intersection(node.names)
        ):
            return False
        if isinstance(node, ast.ExceptHandler) and node.name in trusted_names:
            return False
        if (
            isinstance(node, (ast.MatchAs, ast.MatchStar))
            and node.name in trusted_names
        ):
            return False
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            value = node.value
            if (
                isinstance(value, ast.Name)
                and isinstance(value.ctx, ast.Load)
                and value.id in trusted_names
            ):
                return False

    lifecycle_try = _lifecycle_try(function)
    if lifecycle_try is None:
        return False
    try_index, try_statement = lifecycle_try
    if any(
        isinstance(node, ast.Try) and node.handlers
        for node in ast.walk(function)
    ) or any(
        isinstance(node, (ast.Raise, ast.Return, ast.Yield, ast.YieldFrom))
        for node in ast.walk(function)
    ) or any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pytest"
        and node.func.attr in {"skip", "xfail"}
        for node in ast.walk(function)
    ):
        return False

    top_level = function.body[:try_index]
    protected = try_statement.body

    def _name(node, expected):
        return isinstance(node, ast.Name) and node.id == expected

    def _argument(node, expected):
        kind, value = expected
        if kind == "name":
            return _name(node, value)
        if kind == "constant":
            return isinstance(node, ast.Constant) and node.value == value
        return (
            kind == "str_name"
            and _is_named_call(node, "str")
            and len(node.args) == 1
            and _name(node.args[0], value)
        )

    def _alphagsm_call(call, command, *extra):
        expected = (
            ("name", "env"),
            ("name", "server_name"),
            ("constant", command),
            *extra,
        )
        return (
            _is_named_call(call, "run_and_assert_ok")
            and not call.keywords
            and len(call.args) == len(expected)
            and all(
                _argument(argument, specification)
                for argument, specification in zip(call.args, expected)
            )
        )

    def _statement_call(statement):
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            return statement.value
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
            return statement.value
        return None

    def _target_matches(statement, expected):
        if expected is None:
            return isinstance(statement, ast.Expr)
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            return False
        target = statement.targets[0]
        if isinstance(expected, str):
            return _name(target, expected)
        return (
            isinstance(target, ast.Tuple)
            and len(target.elts) == len(expected)
            and all(_name(item, name) for item, name in zip(target.elts, expected))
        )

    def _required_direct(statements, predicate, target):
        all_calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and predicate(node)
        ]
        direct = []
        for index, statement in enumerate(statements):
            call = _statement_call(statement)
            if call is not None and predicate(call) and _target_matches(statement, target):
                direct.append((index, call))
        if len(all_calls) != 1 or len(direct) != 1 or direct[0][1] is not all_calls[0]:
            return None
        return direct[0][0]

    create_index = _required_direct(
        top_level,
        lambda call: _alphagsm_call(call, "create", ("name", "module_name")),
        None,
    )
    start_index = _required_direct(
        protected,
        lambda call: _alphagsm_call(call, "start"),
        None,
    )
    if game == "moria":
        def _moria_setup(call):
            keywords = {keyword.arg: keyword.value for keyword in call.keywords}
            return (
                _is_named_call(call, "run_setup_with_port_retry")
                and len(call.args) == 4
                and all(
                    _name(argument, expected)
                    for argument, expected in zip(
                        call.args,
                        ("env", "server_name", "port", "install_dir"),
                    )
                )
                and set(keywords) == {"timeout", "steam_app_id"}
                and _name(keywords["timeout"], "SETUP_TIMEOUT")
                and _name(keywords["steam_app_id"], "steam_app_id")
            )

        setup_index = _required_direct(
            top_level,
            _moria_setup,
            ("result", "port"),
        )
    elif game == "forest":
        setup_index = _required_direct(
            top_level,
            lambda call: _alphagsm_call(
                call,
                "setup",
                ("constant", "-n"),
                ("str_name", "port"),
                ("str_name", "install_dir"),
            ),
            "result",
        )
    else:
        return False
    if None in (create_index, setup_index, start_index) or not (
        create_index < setup_index
    ):
        return False

    status_index = _required_direct(
        protected,
        lambda call: _alphagsm_call(call, "status"),
        None,
    )
    query_index = _required_direct(
        protected,
        lambda call: _alphagsm_call(call, "query"),
        "query_result",
    )
    info_index = _required_direct(
        protected,
        lambda call: _alphagsm_call(call, "info"),
        "info_result",
    )
    info_json_index = _required_direct(
        protected,
        lambda call: _alphagsm_call(call, "info", ("constant", "--json")),
        "info_json_result",
    )
    if game == "moria":
        status_ready_index = _required_direct(
            protected,
            lambda call: (
                _is_named_call(call, "wait_for_status_json_running")
                and not call.keywords
                and len(call.args) == 4
                and all(
                    _name(argument, expected)
                    for argument, expected in zip(
                        call.args,
                        ("env", "server_name", "status_json_path", "START_TIMEOUT"),
                    )
                )
            ),
            "status_payload",
        )
        info_ready_index = _required_direct(
            protected,
            lambda call: (
                _is_named_call(call, "wait_for_info_protocol")
                and len(call.args) == 4
                and _name(call.args[0], "env")
                and _name(call.args[1], "server_name")
                and _argument(call.args[2], ("constant", "udp"))
                and _name(call.args[3], "START_TIMEOUT")
                and len(call.keywords) == 1
                and call.keywords[0].arg == "expected_port"
                and _name(call.keywords[0].value, "port")
            ),
            "info_data",
        )
        readiness_indices = (status_ready_index, info_ready_index)
    else:
        readiness_index = _required_direct(
            protected,
            lambda call: (
                _is_named_call(call, "wait_for_log_marker")
                and len(call.args) == 3
                and _name(call.args[0], "server_log")
                and isinstance(call.args[1], ast.List)
                and len(call.args[1].elts) == 1
                and _argument(call.args[1].elts[0], ("constant", "[Logged On"))
                and _name(call.args[2], "START_TIMEOUT")
                and len(call.keywords) == 2
                and _name(call.keywords[0].value, "env")
                and call.keywords[0].arg == "env"
                and _name(call.keywords[1].value, "server_name")
                and call.keywords[1].arg == "server_name"
            ),
            None,
        )
        readiness_indices = (readiness_index,)
    ordered = (
        start_index,
        *readiness_indices,
        status_index,
        query_index,
        info_index,
        info_json_index,
    )
    if any(index is None for index in ordered) or list(ordered) != sorted(ordered):
        return False

    unsafe_message_names = {"info_data", "_info_data", "query_result", "info_result"}
    for assertion in (
        node for node in ast.walk(try_statement) if isinstance(node, ast.Assert)
    ):
        if assertion.msg is not None and any(
            (isinstance(node, ast.Name) and node.id in unsafe_message_names)
            or (isinstance(node, ast.Attribute) and node.attr in {"stdout", "stderr"})
            for node in ast.walk(assertion.msg)
        ):
            return False

    endpoint_name = "wait_for_udp_closed"
    endpoint_port_name = "port" if game == "moria" else "query_port"
    endpoint_index = try_index + 2
    if endpoint_index >= len(function.body):
        return False
    endpoint_call = _statement_call(function.body[endpoint_index])
    return (
        endpoint_call is not None
        and _is_named_call(endpoint_call, endpoint_name)
        and len(endpoint_call.args) == 3
        and _argument(endpoint_call.args[0], ("constant", "127.0.0.1"))
        and _name(endpoint_call.args[1], endpoint_port_name)
        and _name(endpoint_call.args[2], "STOP_TIMEOUT")
    )


def _moria_info_readiness_contract(source):
    function = _function_node(source, "test_returntomoriaserver_lifecycle")
    if function is None:
        return False
    lifecycle_try = _lifecycle_try(function)
    if lifecycle_try is None:
        return False
    _, try_statement = lifecycle_try
    all_status_calls = [
        node
        for node in ast.walk(function)
        if _is_named_call(node, "wait_for_status_json_running")
    ]
    all_info_calls = [
        node
        for node in ast.walk(function)
        if _is_named_call(node, "wait_for_info_protocol")
    ]
    if len(all_status_calls) != 1 or len(all_info_calls) != 1:
        return False
    direct_status = [
        (index, _direct_assignment_call(statement, "status_payload", "wait_for_status_json_running"))
        for index, statement in enumerate(try_statement.body)
    ]
    direct_status = [(index, call) for index, call in direct_status if call is not None]
    direct_info = [
        (index, _direct_assignment_call(statement, "info_data", "wait_for_info_protocol"))
        for index, statement in enumerate(try_statement.body)
    ]
    direct_info = [(index, call) for index, call in direct_info if call is not None]
    if len(direct_status) != 1 or len(direct_info) != 1:
        return False
    status_index, status_call = direct_status[0]
    info_index, info_call = direct_info[0]
    expected_port = next(
        (keyword.value for keyword in info_call.keywords if keyword.arg == "expected_port"),
        None,
    )
    return (
        status_index < info_index
        and status_call is all_status_calls[0]
        and info_call is all_info_calls[0]
        and len(info_call.args) == 4
        and isinstance(info_call.args[0], ast.Name)
        and info_call.args[0].id == "env"
        and isinstance(info_call.args[1], ast.Name)
        and info_call.args[1].id == "server_name"
        and isinstance(info_call.args[2], ast.Constant)
        and info_call.args[2].value == "udp"
        and isinstance(info_call.args[3], ast.Name)
        and info_call.args[3].id == "START_TIMEOUT"
        and isinstance(expected_port, ast.Name)
        and expected_port.id == "port"
    )


def _safe_moria_status_contract(source):
    function = _function_node(source, "_safe_status_diagnostics")
    if function is None:
        return False
    body = function.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 2:
        return False
    type_guard, safe_return = body
    if (
        not isinstance(type_guard, ast.If)
        or not isinstance(type_guard.test, ast.UnaryOp)
        or not isinstance(type_guard.test.op, ast.Not)
        or not _is_named_call(type_guard.test.operand, "isinstance")
        or len(type_guard.test.operand.args) != 2
        or not isinstance(type_guard.test.operand.args[0], ast.Name)
        or type_guard.test.operand.args[0].id != "payload"
        or not isinstance(type_guard.test.operand.args[1], ast.Name)
        or type_guard.test.operand.args[1].id != "dict"
        or type_guard.test.operand.keywords
        or type_guard.orelse
        or len(type_guard.body) != 1
        or not isinstance(type_guard.body[0], ast.Return)
        or not isinstance(type_guard.body[0].value, ast.Constant)
        or type_guard.body[0].value.value is not None
        or not isinstance(safe_return, ast.Return)
        or not isinstance(safe_return.value, ast.DictComp)
    ):
        return False
    dictionary = safe_return.value
    if len(dictionary.generators) != 1:
        return False
    generator = dictionary.generators[0]
    return (
        isinstance(dictionary.key, ast.Name)
        and dictionary.key.id == "field"
        and isinstance(dictionary.value, ast.Subscript)
        and isinstance(dictionary.value.value, ast.Name)
        and dictionary.value.value.id == "payload"
        and isinstance(dictionary.value.slice, ast.Name)
        and dictionary.value.slice.id == "field"
        and isinstance(generator.target, ast.Name)
        and generator.target.id == "field"
        and isinstance(generator.iter, ast.Name)
        and generator.iter.id == "_SAFE_STATUS_DIAGNOSTIC_FIELDS"
        and len(generator.ifs) == 1
        and isinstance(generator.ifs[0], ast.Compare)
        and isinstance(generator.ifs[0].left, ast.Name)
        and generator.ifs[0].left.id == "field"
        and len(generator.ifs[0].ops) == 1
        and isinstance(generator.ifs[0].ops[0], ast.In)
        and len(generator.ifs[0].comparators) == 1
        and isinstance(generator.ifs[0].comparators[0], ast.Name)
        and generator.ifs[0].comparators[0].id == "payload"
    )


def test_assert_alphagsm_result_ok_redacts_failure_message():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "assertion-invite-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=1,
        stdout="",
        stderr=f"InviteCode={invite_code}",
    )

    with pytest.raises(AssertionError) as failure:
        helpers.assert_alphagsm_result_ok(result)

    assert invite_code not in str(failure.value)
    assert "InviteCode=<redacted>" in str(failure.value)


def test_run_and_assert_ok_redacts_assertion_message(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "run-assertion-invite-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "status"],
        returncode=1,
        stdout="",
        stderr=f"InviteCode={invite_code}",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "skip_for_known_steamcmd_issue",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(AssertionError) as failure:
        helpers.run_and_assert_ok({}, "ittestserver", "status")

    assert invite_code not in str(failure.value)
    assert "InviteCode=<redacted>" in str(failure.value)


@pytest.mark.parametrize(
    "diagnostic_exception",
    (
        OSError,
        pytest.fail.Exception,
        pytest.skip.Exception,
        pytest.xfail.Exception,
        KeyboardInterrupt,
        SystemExit,
        GeneratorExit,
    ),
)
def test_run_and_assert_ok_preserves_exact_command_failure_when_diagnostic_raises(
    monkeypatch,
    capsys,
    diagnostic_exception,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    diagnostic_secret = "runtime-diagnostic-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "status"],
        returncode=1,
        stdout="",
        stderr="command failed",
    )
    command_failure = AssertionError("original command failure")

    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "skip_for_known_steamcmd_issue",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        helpers,
        "assert_alphagsm_result_ok",
        lambda _result: (_ for _ in ()).throw(command_failure),
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            diagnostic_exception(f"AWS_SECRET_ACCESS_KEY={diagnostic_secret}")
        ),
    )

    surfaced = None
    try:
        helpers.run_and_assert_ok({}, "ittestserver", "status")
    except BaseException as exc:  # noqa: BLE001 - control paths are the contract
        surfaced = exc
    else:
        pytest.fail("run_and_assert_ok unexpectedly succeeded")

    assert surfaced is command_failure
    captured = capsys.readouterr().out
    assert diagnostic_secret not in captured
    assert "AWS_SECRET_ACCESS_KEY=<redacted>" in captured


def test_run_and_assert_ok_clears_raw_failure_state_from_traceback(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env_secret = "run-env-secret"
    arg_secret = "run-argument-secret"
    result_secret = "run-result-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "--join-code", arg_secret],
        returncode=1,
        stdout="",
        stderr=f"InviteCode={result_secret}",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "skip_for_known_steamcmd_issue",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(AssertionError) as failure:
        helpers.run_and_assert_ok(
            {"ADMIN_PASSWORD": env_secret},
            "ittestserver",
            "status",
            "--join-code",
            arg_secret,
        )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "run_and_assert_ok",
        "assert_alphagsm_result_ok",
    )
    assert env_secret not in traceback_locals
    assert arg_secret not in traceback_locals
    assert result_secret not in traceback_locals


def test_run_alphagsm_raises_fresh_redacted_timeout_and_clears_raw_locals(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env_secret = "run-timeout-env-secret"
    command_secret = "run-timeout-command-secret"
    output_secret = "run-timeout-output-secret"
    stderr_secret = "run-timeout-stderr-secret"
    raw_timeout = subprocess.TimeoutExpired(
        ["alphagsm", "ittestserver", "--join-code", command_secret],
        timeout=30,
        output=f"AWS_SECRET_ACCESS_KEY={output_secret}",
        stderr=f"DATABASE_PASSWORD_FILE={stderr_secret}",
    )
    monkeypatch.setattr(
        helpers.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(raw_timeout),
    )

    with pytest.raises(subprocess.TimeoutExpired) as failure:
        helpers.run_alphagsm(
            {"DATABASE_PASSWORD_FILE": env_secret},
            "ittestserver",
            "start",
            "--join-code",
            command_secret,
            timeout=30,
        )

    surfaced = failure.value
    exposed = "\n".join(
        (
            str(surfaced),
            repr(surfaced.cmd),
            repr(surfaced.output),
            repr(surfaced.stderr),
            _owned_traceback_locals(surfaced, "run_alphagsm"),
        )
    )
    assert surfaced is not raw_timeout
    assert surfaced.__cause__ is None
    assert surfaced.__context__ is None
    assert env_secret not in exposed
    assert command_secret not in exposed
    assert output_secret not in exposed
    assert stderr_secret not in exposed
    assert exposed.count("<redacted>") >= 3


@pytest.mark.parametrize("exception_type", (OSError, subprocess.SubprocessError))
def test_run_alphagsm_raises_fresh_redacted_execution_error(
    monkeypatch,
    exception_type,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env_secret = "run-execution-env-secret"
    command_secret = "run-execution-command-secret"
    exception_secret = "run-execution-exception-secret"
    raw_error = exception_type(f"AWS_SECRET_ACCESS_KEY={exception_secret}")
    monkeypatch.setattr(
        helpers.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(raw_error),
    )

    with pytest.raises(exception_type) as failure:
        helpers.run_alphagsm(
            {"DATABASE_PASSWORD_FILE": env_secret},
            "ittestserver",
            "start",
            "--join-code",
            command_secret,
        )

    surfaced = failure.value
    exposed = str(surfaced) + _owned_traceback_locals(surfaced, "run_alphagsm")
    assert surfaced is not raw_error
    assert surfaced.__cause__ is None
    assert surfaced.__context__ is None
    assert env_secret not in exposed
    assert command_secret not in exposed
    assert exception_secret not in exposed
    assert "AWS_SECRET_ACCESS_KEY=<redacted>" in exposed


def test_run_alphagsm_preserves_successful_completed_process_identity(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "status"],
        returncode=0,
        stdout="running",
        stderr="",
    )
    monkeypatch.setattr(helpers.subprocess, "run", lambda *args, **kwargs: result)

    returned = helpers.run_alphagsm({}, "ittestserver", "status")

    assert returned is result


def test_run_and_assert_ok_returns_sanitized_success_clone(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    arg_secret = "success-argument-secret"
    stdout_secret = "success-stdout-secret"
    stderr_secret = "success-stderr-secret"
    raw_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "--join-code", arg_secret],
        returncode=0,
        stdout=f'{{"protocol":"udp","InviteCode":"{stdout_secret}"}}',
        stderr=f"JoinCode={stderr_secret}",
    )
    seen_results = []
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: raw_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda name, result, **kwargs: seen_results.append(result),
    )

    returned = helpers.run_and_assert_ok(
        {},
        "ittestserver",
        "status",
        "--join-code",
        arg_secret,
    )

    assert seen_results == [raw_result]
    assert returned is not raw_result
    assert returned.returncode == 0
    assert json.loads(returned.stdout) == {
        "protocol": "udp",
        "InviteCode": "<redacted>",
    }
    exposed = repr(returned.args) + returned.stdout + returned.stderr
    assert arg_secret not in exposed
    assert stdout_secret not in exposed
    assert stderr_secret not in exposed


def test_run_and_assert_ok_can_disable_known_steamcmd_skip(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "strict-lifecycle-invite-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "setup"],
        returncode=1,
        stdout="",
        stderr=f"ENABLED (BYO): assets required InviteCode={invite_code}",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(AssertionError) as failure:
        helpers.run_and_assert_ok(
            {},
            "ittestserver",
            "setup",
            allow_known_steamcmd_skip=False,
        )

    assert invite_code not in str(failure.value)
    assert "InviteCode=<redacted>" in str(failure.value)


def test_alphagsm_env_repr_redacts_secrets_but_lookup_keeps_exact_values(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    token_secret = "environment-gh-token-secret"
    password_secret = "environment-password-secret"
    monkeypatch.setenv("GH_TOKEN", token_secret)
    monkeypatch.setenv("ADMIN_PASSWORD", password_secret)
    monkeypatch.setenv("SAFE_SETTING", "visible-setting")

    env = helpers.alphagsm_env(tmp_path / "alphagsm.conf")

    assert env["GH_TOKEN"] == token_secret
    assert env["ADMIN_PASSWORD"] == password_secret
    assert env["SAFE_SETTING"] == "visible-setting"
    assert token_secret not in repr(env)
    assert password_secret not in repr(env)
    assert "visible-setting" in repr(env)
    assert token_secret not in repr(env.copy())
    assert env.copy()["GH_TOKEN"] == token_secret


def test_wait_for_a2s_ready_fails_even_when_tcp_is_open_and_logs_exist(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic query failure used to drive the timeout path."""

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda host, port, timeout=2.0, phase2_timeout=None: (
        (_ for _ in ()).throw(FakeQueryError("udp timeout"))
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    class _DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConn(),
    )

    log_path = tmp_path / "server.log"
    log_path.write_text("Server is hibernating\n", encoding="utf-8")

    dumped = []
    monkeypatch.setattr(
        helpers,
        "_dump_log",
        lambda path, context=None: dumped.append((path, context)),
    )

    with pytest.raises(pytest.fail.Exception, match="A2S on 127.0.0.1:27015 never responded"):
        helpers.wait_for_a2s_ready(
            "127.0.0.1",
            27015,
            5,
            log_path=log_path,
            tcp_port=27015,
        )

    assert dumped == [(log_path, "A2S timeout on port 27015")]


def test_wait_for_a2s_ready_preserves_timeout_when_tcp_probe_raises_non_oserror(
    monkeypatch,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic query failure used to drive the timeout path."""

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda *args, **kwargs: (_ for _ in ()).throw(
        FakeQueryError("udp timeout")
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("non-oserror probe mutation")
        ),
    )

    with pytest.raises(
        pytest.fail.Exception,
        match="A2S on 127.0.0.1:27015 never responded",
    ):
        helpers.wait_for_a2s_ready("127.0.0.1", 27015, 5)

    captured = capsys.readouterr().out
    assert "A2S TCP probe diagnostic collection failed" in captured
    assert "non-oserror probe mutation" in captured


def test_wait_for_a2s_ready_keeps_tcp_open_summary(monkeypatch, capsys):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic query failure used to drive the timeout path."""

    class _DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda *args, **kwargs: (_ for _ in ()).throw(
        FakeQueryError("udp timeout")
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConn(),
    )

    with pytest.raises(pytest.fail.Exception):
        helpers.wait_for_a2s_ready("127.0.0.1", 27015, 5)

    captured = capsys.readouterr().out
    assert "TCP port 127.0.0.1:27015 is open" in captured


def test_wait_for_a2s_ready_clears_query_secret_from_timeout_traceback(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    invite_code = "a2s-traceback-invite-secret"

    class FakeQueryError(OSError):
        """Synthetic query failure carrying sensitive diagnostic text."""

    class _DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda *args, **kwargs: (_ for _ in ()).throw(
        FakeQueryError(f"InviteCode={invite_code}")
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConn(),
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.wait_for_a2s_ready("127.0.0.1", 27015, 5)

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "wait_for_a2s_ready",
        "fail_readiness_timeout",
    )
    assert invite_code not in traceback_locals


def test_wait_for_a2s_ready_routes_tcp_probe_through_diagnostics():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    source = inspect.getsource(helpers.wait_for_a2s_ready)

    assert _a2s_tcp_probe_is_diagnostic(source)


def test_a2s_ast_guard_rejects_comment_label_decoy():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    source = inspect.getsource(helpers.wait_for_a2s_ready)
    mutated = source.replace('"A2S TCP probe"', '"Renamed probe"')
    mutated += '\n# "A2S TCP probe"\n'

    assert not _a2s_tcp_probe_is_diagnostic(mutated)


def test_wait_for_udp_open_retries_until_success(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic UDP reachability failure."""

    attempts = []

    def _fake_udp_ping(host, port, timeout=2.0):
        attempts.append((host, port, timeout))
        if len(attempts) < 2:
            raise FakeQueryError("udp timeout")
        return 1.5

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.udp_ping = _fake_udp_ping
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 1.0, 1.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 1.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    helpers.wait_for_udp_open("127.0.0.1", 27015, 5)

    assert len(attempts) == 2


def test_wait_for_log_marker_dumps_runtime_logs_when_context_provided(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    dumped_runtime = []
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda env, server_name, lines=200: dumped_runtime.append((env, server_name, lines)),
    )
    monkeypatch.setattr(helpers, "_dump_log", lambda path, context=None: None)

    missing_log = tmp_path / "missing.log"

    with pytest.raises(pytest.fail.Exception, match="Log never showed readiness markers"):
        helpers.wait_for_log_marker(
            missing_log,
            ["ready"],
            5,
            env={"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            server_name="ittestserver",
        )

    assert dumped_runtime == [({"ALPHAGSM_CONFIG_LOCATION": "dummy"}, "ittestserver", 200)]


def test_wait_for_glob_log_marker_dumps_runtime_logs_when_context_provided(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    dumped_runtime = []
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda env, server_name, lines=200: dumped_runtime.append((env, server_name, lines)),
    )
    monkeypatch.setattr(helpers, "_dump_log", lambda path, context=None: None)

    with pytest.raises(pytest.fail.Exception, match="Log never showed readiness markers"):
        helpers.wait_for_glob_log_marker(
            tmp_path,
            "*.log",
            ["ready"],
            5,
            env={"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            server_name="itglobserver",
        )

    assert dumped_runtime == [({"ALPHAGSM_CONFIG_LOCATION": "dummy"}, "itglobserver", 200)]


def test_fail_readiness_timeout_dumps_runtime_logs_before_failing(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    events = []

    class ReadinessFailure(Exception):
        """Synthetic failure used to observe diagnostic ordering."""

    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda actual_env, server_name: events.append(
            ("runtime-dump", actual_env, server_name)
        ),
    )

    def _fail(message):
        events.append(("fail", message))
        raise ReadinessFailure(message)

    monkeypatch.setattr(helpers.pytest, "fail", _fail)

    with pytest.raises(ReadinessFailure, match="custom readiness evidence"):
        helpers.fail_readiness_timeout(
            env,
            "ittestserver",
            "custom readiness evidence",
        )

    assert events == [
        ("runtime-dump", env, "ittestserver"),
        ("fail", "custom readiness evidence"),
    ]


def test_fail_readiness_timeout_retains_supplied_failure_message(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda env, server_name: None,
    )

    message = "Status.json timeout; last payload={'Status': 'starting'}"
    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.fail_readiness_timeout({}, "itreturntomo", message)

    assert str(failure.value) == message


def test_fail_readiness_timeout_survives_diagnostic_collection_error(
    monkeypatch,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    diagnostic_secret = "collector-secret"

    def _raise_diagnostic_error(env, server_name):
        raise OSError(f"token={diagnostic_secret}")

    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        _raise_diagnostic_error,
    )

    message = "Return to Moria did not become ready"
    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.fail_readiness_timeout({}, "itreturntomo", message)

    captured = capsys.readouterr().out
    assert str(failure.value) == message
    assert "Runtime diagnostic collection failed" in captured
    assert diagnostic_secret not in captured
    assert "token=<redacted>" in captured


@pytest.mark.parametrize(
    "outcome_type",
    (pytest.fail.Exception, pytest.skip.Exception, pytest.xfail.Exception),
)
def test_fail_readiness_timeout_ignores_diagnostic_pytest_outcomes(outcome_type):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    def _raise_outcome():
        raise outcome_type("diagnostic outcome")

    try:
        helpers.fail_readiness_timeout(
            None,
            None,
            "intended readiness timeout",
            diagnostics=(("Mutation", _raise_outcome),),
        )
    except BaseException as failure:  # pylint: disable=broad-exception-caught
        assert isinstance(failure, pytest.fail.Exception)
        assert str(failure) == "intended readiness timeout"
    else:
        raise AssertionError("Expected readiness timeout failure")


@pytest.mark.parametrize(
    "control_exception",
    (KeyboardInterrupt, SystemExit, GeneratorExit),
)
def test_fail_readiness_timeout_preserves_timeout_on_control_diagnostic_exception(
    control_exception,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    diagnostic_secret = "readiness-control-diagnostic-secret"

    def _raise_control_exception():
        raise control_exception(f"AWS_SECRET_ACCESS_KEY={diagnostic_secret}")

    with pytest.raises(pytest.fail.Exception, match="intended readiness timeout"):
        helpers.fail_readiness_timeout(
            None,
            None,
            "intended readiness timeout",
            diagnostics=(("Mutation", _raise_control_exception),),
        )

    captured = capsys.readouterr().out
    assert diagnostic_secret not in captured
    assert "AWS_SECRET_ACCESS_KEY=<redacted>" in captured


def test_wait_for_info_protocol_preserves_timeout_when_diagnostics_raise(
    monkeypatch,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "info", "--json"],
        returncode=1,
        stdout="",
        stderr="not ready",
    )
    log_secret = "info-log-secret"
    runtime_secret = "info-runtime-secret"

    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"InviteCode={log_secret}")
        ),
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"token={runtime_secret}")
        ),
    )

    with pytest.raises(
        pytest.fail.Exception,
        match="info --json never returned protocol",
    ):
        helpers.wait_for_info_protocol({}, "ittestserver", "a2s", 5)

    captured = capsys.readouterr().out
    assert log_secret not in captured
    assert runtime_secret not in captured


def test_wait_for_runtime_log_marker_preserves_timeout_when_diagnostics_raise(
    monkeypatch,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=1,
        stdout="still starting",
        stderr="",
    )
    log_secret = "runtime-log-secret"
    runtime_secret = "runtime-dump-secret"

    monkeypatch.setattr(
        helpers.time,
        "monotonic",
        _retaining_clock(0.0, 0.0, 10.0),
    )
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"JoinCode={log_secret}")
        ),
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"token={runtime_secret}")
        ),
    )

    with pytest.raises(
        pytest.fail.Exception,
        match="Runtime logs never showed readiness markers",
    ):
        helpers.wait_for_runtime_log_marker({}, "ittestserver", ["ready"], 5)

    captured = capsys.readouterr().out
    assert log_secret not in captured
    assert runtime_secret not in captured


def test_wait_for_log_marker_preserves_timeout_when_diagnostics_raise(
    monkeypatch,
    tmp_path,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    local_secret = "local-tail-secret"
    runtime_secret = "local-runtime-secret"
    log_path = tmp_path / "server.log"
    log_path.write_text("still starting\n", encoding="utf-8")

    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        helpers,
        "_dump_log",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"JoinCode={local_secret}")
        ),
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"token={runtime_secret}")
        ),
    )

    with pytest.raises(
        pytest.fail.Exception,
        match="Log never showed readiness markers",
    ):
        helpers.wait_for_log_marker(
            log_path,
            ["ready"],
            5,
            env={},
            server_name="ittestserver",
        )

    captured = capsys.readouterr().out
    assert local_secret not in captured
    assert runtime_secret not in captured


def test_wait_for_info_protocol_clears_secrets_from_timeout_traceback(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "info-traceback-invite-secret"
    env_secret = "info-traceback-env-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "info", "--json"],
        returncode=0,
        stdout=json.dumps(
            {
                "protocol": "tcp",
                "port": 27015,
                "InviteCode": invite_code,
            }
        ),
        stderr="",
    )
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.wait_for_info_protocol(
            {"ADMIN_PASSWORD": env_secret},
            "ittestserver",
            "udp",
            5,
        )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "wait_for_info_protocol",
        "fail_readiness_timeout",
    )
    assert invite_code not in traceback_locals
    assert env_secret not in traceback_locals


def test_wait_for_runtime_log_marker_clears_secrets_from_timeout_traceback(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "runtime-traceback-invite-secret"
    env_secret = "runtime-traceback-env-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=1,
        stdout=f"InviteCode={invite_code}",
        stderr="",
    )
    monkeypatch.setattr(
        helpers.time,
        "monotonic",
        _retaining_clock(0.0, 0.0, 10.0),
    )
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.wait_for_runtime_log_marker(
            {"ADMIN_PASSWORD": env_secret},
            "ittestserver",
            ["ready"],
            5,
        )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "wait_for_runtime_log_marker",
        "fail_readiness_timeout",
    )
    assert invite_code not in traceback_locals
    assert env_secret not in traceback_locals


@pytest.mark.parametrize("use_glob_wait", (False, True))
def test_log_marker_timeout_clears_secrets_from_traceback(
    monkeypatch,
    tmp_path,
    use_glob_wait,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "local-traceback-invite-secret"
    env_secret = "local-traceback-env-secret"
    log_path = tmp_path / "connection.log"
    log_path.write_text(f"InviteCode={invite_code}\n", encoding="utf-8")
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    with pytest.raises(pytest.fail.Exception) as failure:
        if use_glob_wait:
            helpers.wait_for_glob_log_marker(
                tmp_path,
                "*.log",
                ["ready"],
                5,
                env={"ADMIN_PASSWORD": env_secret},
                server_name="ittestserver",
            )
        else:
            helpers.wait_for_log_marker(
                log_path,
                ["ready"],
                5,
                env={"ADMIN_PASSWORD": env_secret},
                server_name="ittestserver",
            )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "wait_for_log_marker",
        "wait_for_glob_log_marker",
        "fail_readiness_timeout",
    )
    assert invite_code not in traceback_locals
    assert env_secret not in traceback_locals


@pytest.mark.parametrize("use_glob_wait", (False, True))
def test_log_marker_success_returns_redacted_text(
    tmp_path,
    use_glob_wait,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "local-return-invite-secret"
    log_path = tmp_path / "connection.log"
    log_path.write_text(
        f"ready\nInviteCode={invite_code}\n",
        encoding="utf-8",
    )

    if use_glob_wait:
        returned = helpers.wait_for_glob_log_marker(
            tmp_path,
            "*.log",
            ["ready"],
            5,
        )
    else:
        returned = helpers.wait_for_log_marker(log_path, ["ready"], 5)

    assert invite_code not in returned
    assert "InviteCode=<redacted>" in returned


@pytest.mark.parametrize(
    "helper_name",
    (
        "wait_for_info_protocol",
        "wait_for_runtime_log_marker",
        "wait_for_log_marker",
        "wait_for_glob_log_marker",
        "wait_for_a2s_ready",
        "wait_for_tcp_open",
        "wait_for_udp_open",
        "wait_for_quake_ready",
        "wait_for_quakeworld_ready",
        "wait_for_quake2_ready",
    ),
)
def test_readiness_timeout_helpers_use_shared_failure_router(helper_name):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    source = inspect.getsource(getattr(helpers, helper_name))

    assert _uses_shared_readiness_failure(source, helper_name)


def test_readiness_router_ast_guard_rejects_renamed_call_with_comment_decoy():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    source = inspect.getsource(helpers.wait_for_tcp_open)
    mutated = source.replace("fail_readiness_timeout(", "renamed_timeout(")
    mutated += "\n# fail_readiness_timeout(...)\n"

    assert not _uses_shared_readiness_failure(mutated, "wait_for_tcp_open")


def test_runtime_probe_hosts_include_docker_bridge_gateway(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    route_file = tmp_path / "route"
    route_file.write_text(
        "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
        "eth0 00000000 010011AC 0003 0 0 0 00000000 0 0 0\n",
        encoding="ascii",
    )
    monkeypatch.setattr(helpers, "DOCKER_ROUTE_FILE", str(route_file))
    monkeypatch.setattr(
        helpers.os.path,
        "exists",
        lambda path: path == "/.dockerenv",
    )

    assert helpers._runtime_probe_hosts("127.0.0.1") == (
        "127.0.0.1",
        "172.17.0.1",
    )


def test_runtime_probe_hosts_preserve_explicit_host_and_deduplicate(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_docker_bridge_gateway",
        lambda: "172.17.0.1",
    )
    monkeypatch.setattr(
        helpers.os.path,
        "exists",
        lambda path: path == "/.dockerenv",
    )

    assert helpers._runtime_probe_hosts("172.17.0.1") == (
        "172.17.0.1",
        "127.0.0.1",
    )


def test_wait_for_tcp_closed_requires_loopback_and_docker_gateway(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    attempts = []

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def _connect(address, timeout):
        attempts.append((address, timeout))
        if address[0] == "172.17.0.1":
            return _Connection()
        raise OSError("closed")

    monkeypatch.setattr(helpers, "_runtime_probe_hosts", lambda _host: (
        "127.0.0.1",
        "172.17.0.1",
    ))
    monkeypatch.setattr(helpers.socket, "create_connection", _connect)
    clock = iter((0.0, 0.0, 1.1))
    monkeypatch.setattr(helpers.time, "time", lambda: next(clock, 1.1))
    monkeypatch.setattr(helpers.time, "sleep", lambda _seconds: None)

    with pytest.raises(AssertionError, match="still open"):
        helpers.wait_for_tcp_closed("127.0.0.1", 25565, 1)

    assert attempts[0][0] == ("127.0.0.1", 25565)
    assert attempts[1][0] == ("172.17.0.1", 25565)


def test_wait_for_udp_open_tries_the_docker_gateway(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    query_utils = importlib.import_module("utils.query")
    attempts = []

    def _udp_ping(host, _port):
        attempts.append(host)
        if host == "127.0.0.1":
            raise query_utils.QueryError("manager loopback has no sibling server")

    monkeypatch.setattr(
        helpers,
        "_runtime_probe_hosts",
        lambda _host: ("127.0.0.1", "172.17.0.1"),
    )
    monkeypatch.setattr(query_utils, "udp_ping", _udp_ping)

    helpers.wait_for_udp_open("127.0.0.1", 25565, 1)

    assert attempts == ["127.0.0.1", "172.17.0.1"]


def test_capture_alphagsm_stop_preserves_lifecycle_failure_on_stop_timeout(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_timeout = subprocess.TimeoutExpired(
        ["alphagsm", "ittestserver", "stop"],
        timeout=90,
    )

    def _raise_stop_timeout(*args, **kwargs):
        raise stop_timeout

    monkeypatch.setattr(helpers, "run_alphagsm", _raise_stop_timeout)

    with pytest.raises(RuntimeError, match="lifecycle failed"):
        try:
            raise RuntimeError("lifecycle failed")
        finally:
            helpers.capture_alphagsm_stop(
                {},
                "ittestserver",
                sys.exc_info()[1],
                timeout=90,
            )


def test_capture_alphagsm_stop_preserves_lifecycle_failure_on_log_error(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout="",
        stderr="",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: stop_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("log failed")),
    )

    with pytest.raises(RuntimeError, match="lifecycle failed"):
        try:
            raise RuntimeError("lifecycle failed")
        finally:
            helpers.capture_alphagsm_stop(
                {},
                "ittestserver",
                sys.exc_info()[1],
            )


def test_capture_alphagsm_stop_surfaces_timeout_without_lifecycle_failure(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    command_secret = "standalone-timeout-command-secret"
    output_secret = "standalone-timeout-output-secret"
    stderr_secret = "standalone-timeout-stderr-secret"
    stop_timeout = subprocess.TimeoutExpired(
        ["alphagsm", "ittestserver", "stop", "--join-code", command_secret],
        timeout=90,
        output=f"InviteCode={output_secret}",
        stderr=f"JoinCode={stderr_secret}",
    )

    def _raise_stop_timeout(*args, **kwargs):
        raise stop_timeout

    monkeypatch.setattr(helpers, "run_alphagsm", _raise_stop_timeout)

    with pytest.raises(subprocess.TimeoutExpired) as failure:
        helpers.capture_alphagsm_stop(
            {"ADMIN_PASSWORD": "standalone-timeout-env-secret"},
            "ittestserver",
            None,
            timeout=90,
        )

    surfaced = failure.value
    exposed = "\n".join(
        (
            str(surfaced),
            repr(surfaced.cmd),
            repr(surfaced.output),
            repr(surfaced.stderr),
            _owned_traceback_locals(surfaced, "capture_alphagsm_stop"),
        )
    )
    assert command_secret not in exposed
    assert output_secret not in exposed
    assert stderr_secret not in exposed
    assert "standalone-timeout-env-secret" not in exposed
    assert surfaced.__cause__ is None
    assert surfaced.__context__ is None
    assert exposed.count("<redacted>") >= 3


def test_capture_alphagsm_stop_surfaces_log_error_without_lifecycle_failure(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    log_secret = "standalone-logging-secret"
    result_secret = "standalone-result-secret"
    env_secret = "standalone-logging-env-secret"
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout=f"InviteCode={result_secret}",
        stderr="",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: stop_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(f"JoinCode={log_secret}")
        ),
    )

    with pytest.raises(OSError) as failure:
        helpers.capture_alphagsm_stop(
            {"ADMIN_PASSWORD": env_secret},
            "ittestserver",
            None,
        )

    surfaced = failure.value
    exposed = str(surfaced) + _owned_traceback_locals(
        surfaced,
        "capture_alphagsm_stop",
    )
    assert log_secret not in exposed
    assert result_secret not in exposed
    assert env_secret not in exposed
    assert "<redacted>" in exposed
    assert surfaced.__cause__ is None
    assert surfaced.__context__ is None


@pytest.mark.parametrize("outcome", (pytest.fail, pytest.skip, pytest.xfail))
@pytest.mark.parametrize("stage", ("stop", "logging"))
def test_capture_alphagsm_stop_preserves_lifecycle_failure_on_pytest_outcome(
    monkeypatch,
    outcome,
    stage,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout="",
        stderr="",
    )

    def _raise_outcome(*args, **kwargs):
        outcome("cleanup outcome")

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        _raise_outcome if stage == "stop" else lambda *args, **kwargs: stop_result,
    )
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        _raise_outcome if stage == "logging" else lambda *args, **kwargs: None,
    )

    lifecycle_failure = RuntimeError("lifecycle failed")
    surfaced = None
    try:
        try:
            raise lifecycle_failure
        finally:
            helpers.capture_alphagsm_stop(
                {},
                "ittestserver",
                sys.exc_info()[1],
            )
    except BaseException as exc:  # noqa: BLE001 - control paths are the contract
        surfaced = exc
    else:
        pytest.fail("lifecycle failure was swallowed")

    assert surfaced is lifecycle_failure


@pytest.mark.parametrize("outcome", (pytest.fail, pytest.skip, pytest.xfail))
@pytest.mark.parametrize("stage", ("stop", "logging"))
def test_capture_alphagsm_stop_reraises_standalone_pytest_outcome(
    monkeypatch,
    outcome,
    stage,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout="",
        stderr="",
    )

    outcome_secret = "standalone-outcome-secret"

    def _raise_outcome(*args, **kwargs):
        outcome(f"InviteCode={outcome_secret}")

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        _raise_outcome if stage == "stop" else lambda *args, **kwargs: stop_result,
    )
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        _raise_outcome if stage == "logging" else lambda *args, **kwargs: None,
    )

    with pytest.raises(outcome.Exception) as failure:
        helpers.capture_alphagsm_stop({}, "ittestserver", None)

    assert outcome_secret not in str(failure.value)
    assert "<redacted>" in str(failure.value)
    assert failure.value.__cause__ is None
    assert failure.value.__context__ is None


@pytest.mark.parametrize(
    "control_exception",
    (KeyboardInterrupt, SystemExit, GeneratorExit),
)
@pytest.mark.parametrize("stage", ("stop", "logging"))
def test_capture_alphagsm_stop_preserves_exact_lifecycle_failure_on_control_exception(
    monkeypatch,
    control_exception,
    stage,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout="",
        stderr="",
    )

    def _raise_control(*args, **kwargs):
        raise control_exception("control")

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        _raise_control if stage == "stop" else lambda *args, **kwargs: stop_result,
    )
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        _raise_control if stage == "logging" else lambda *args, **kwargs: None,
    )

    lifecycle_failure = RuntimeError("lifecycle failed")
    surfaced = None
    try:
        try:
            raise lifecycle_failure
        finally:
            helpers.capture_alphagsm_stop(
                {},
                "ittestserver",
                sys.exc_info()[1],
            )
    except BaseException as exc:  # noqa: BLE001 - control paths are the contract
        surfaced = exc
    else:
        pytest.fail("lifecycle failure was swallowed")

    assert surfaced is lifecycle_failure


@pytest.mark.parametrize(
    "control_exception",
    (KeyboardInterrupt, SystemExit, GeneratorExit),
)
@pytest.mark.parametrize("stage", ("stop", "logging"))
def test_capture_alphagsm_stop_propagates_exact_standalone_control_exception(
    monkeypatch,
    control_exception,
    stage,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout="",
        stderr="",
    )
    control = control_exception("standalone control")

    def _raise_control(*args, **kwargs):
        raise control

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        _raise_control if stage == "stop" else lambda *args, **kwargs: stop_result,
    )
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        _raise_control if stage == "logging" else lambda *args, **kwargs: None,
    )

    with pytest.raises(control_exception) as failure:
        helpers.capture_alphagsm_stop({}, "ittestserver", None)

    assert failure.value is control


def test_capture_alphagsm_stop_clears_raw_state_from_standalone_traceback(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env_secret = "cleanup-env-secret"
    result_secret = "cleanup-result-secret"
    stop_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout=f"InviteCode={result_secret}",
        stderr="",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: stop_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda *args, **kwargs: pytest.fail("logging outcome"),
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        helpers.capture_alphagsm_stop(
            {"ADMIN_PASSWORD": env_secret},
            "ittestserver",
            None,
        )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "capture_alphagsm_stop",
    )
    assert env_secret not in traceback_locals
    assert result_secret not in traceback_locals


def test_capture_alphagsm_stop_preserves_lifecycle_when_reporting_raises_outcome(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("stop failed")),
    )
    monkeypatch.setattr(
        helpers,
        "_redact_logged_text",
        lambda value: pytest.fail("reporting outcome"),
    )

    with pytest.raises(RuntimeError, match="lifecycle failed"):
        try:
            raise RuntimeError("lifecycle failed")
        finally:
            helpers.capture_alphagsm_stop(
                {},
                "ittestserver",
                sys.exc_info()[1],
            )


def test_capture_alphagsm_stop_returns_failure_for_post_finally_assertion(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    stop_failure = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=1,
        stdout="",
        stderr="stop failed",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: stop_failure)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    stop_result = helpers.capture_alphagsm_stop({}, "ittestserver", None)

    with pytest.raises(AssertionError, match="stop failed"):
        assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout


def test_capture_alphagsm_stop_returns_sanitized_success_clone(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "stop-success-invite-secret"
    raw_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "stop"],
        returncode=0,
        stdout=f"InviteCode={invite_code}",
        stderr="",
    )
    logged = []
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: raw_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda name, result: logged.append(result),
    )

    returned = helpers.capture_alphagsm_stop({}, "ittestserver", None)

    assert logged == [raw_result]
    assert returned is not raw_result
    assert invite_code not in returned.stdout
    assert returned.stdout == "InviteCode=<redacted>"


@pytest.mark.parametrize(
    ("test_file", "function_name"),
    (
        ("test_returntomoriaserver.py", "test_returntomoriaserver_lifecycle"),
        ("test_theforestserver.py", "test_theforestserver_lifecycle"),
    ),
)
def test_lifecycle_cleanup_uses_exception_preserving_stop_helper(
    test_file,
    function_name,
):
    integration_test = Path(__file__).parents[1] / "integration_tests" / test_file
    source = integration_test.read_text(encoding="utf-8")

    assert _lifecycle_cleanup_contract(source, function_name)


@pytest.mark.parametrize(
    "source",
    (
        """
def lifecycle():
    try:
        pass
    finally:
        pass
    # stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        pass
    finally:
        stop_result = renamed_stop_helper(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        pass
    finally:
        pass
    stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
    ),
)
def test_lifecycle_cleanup_ast_guard_rejects_decoy_rename_and_moved_code(source):
    assert not _lifecycle_cleanup_contract(source, "lifecycle")


@pytest.mark.parametrize(
    "source",
    (
        """
def lifecycle():
    try:
        lifecycle_step()
    except Exception:
        pass
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        try:
            lifecycle_step()
        except Exception:
            pass
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        lifecycle_step()
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    return
    assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        lifecycle_step()
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    if False:
        assert_alphagsm_result_ok(stop_result)
    # assert_alphagsm_result_ok(stop_result)
""",
        """
def lifecycle():
    try:
        return
        lifecycle_step()
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1])
    assert_alphagsm_result_ok(stop_result)
""",
    ),
)
def test_lifecycle_cleanup_ast_guard_rejects_swallowed_or_unreachable_failures(
    source,
):
    assert not _lifecycle_cleanup_contract(source, "lifecycle")


@pytest.mark.parametrize(
    ("test_file", "function_name", "game"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
        ),
    ),
)
def test_game_lifecycle_ast_contract_requires_direct_unconditional_flow(
    test_file,
    function_name,
    game,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file

    assert _game_lifecycle_contract(
        source_path.read_text(encoding="utf-8"),
        function_name,
        game,
    )


@pytest.mark.parametrize(
    ("test_file", "function_name", "game", "old", "new"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '    run_and_assert_ok(env, server_name, "create", module_name)',
            '    if False:\n        run_and_assert_ok(env, server_name, "create", module_name)',
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            "    result, port = run_setup_with_port_retry(",
            "    if False:\n        result, port = run_setup_with_port_retry(",
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        run_and_assert_ok(env, server_name, "start")',
            '        if False:\n            run_and_assert_ok(env, server_name, "start")',
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            "        status_payload = wait_for_status_json_running(",
            "        if False:\n            status_payload = wait_for_status_json_running(",
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        run_and_assert_ok(env, server_name, "status")',
            '        if False:\n            run_and_assert_ok(env, server_name, "status")',
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        query_result = run_and_assert_ok(env, server_name, "query")',
            '        for _unused in ():\n            query_result = run_and_assert_ok(env, server_name, "query")',
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        info_result = run_and_assert_ok(env, server_name, "info")',
            '        if False:\n            info_result = run_and_assert_ok(env, server_name, "info")',
        ),
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")',
            '        for _unused in ():\n            info_json_result = run_and_assert_ok(env, server_name, "info", "--json")',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '    run_and_assert_ok(env, server_name, "create", module_name)',
            '    if False:\n        run_and_assert_ok(env, server_name, "create", module_name)',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))',
            '    for _unused in ():\n        result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        run_and_assert_ok(env, server_name, "start")',
            '        if False:\n            run_and_assert_ok(env, server_name, "start")',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            "        wait_for_log_marker(",
            "        if False:\n            wait_for_log_marker(",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        run_and_assert_ok(env, server_name, "status")',
            '        if False:\n            run_and_assert_ok(env, server_name, "status")',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        query_result = run_and_assert_ok(env, server_name, "query")',
            '        for _unused in ():\n            query_result = run_and_assert_ok(env, server_name, "query")',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        info_result = run_and_assert_ok(env, server_name, "info")',
            '        if False:\n            info_result = run_and_assert_ok(env, server_name, "info")',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")',
            '        for _unused in ():\n            info_json_result = run_and_assert_ok(env, server_name, "info", "--json")',
        ),
    ),
)
def test_game_lifecycle_ast_contract_rejects_nested_required_calls(
    test_file,
    function_name,
    game,
    old,
    new,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    mutated = source.replace(old, new, 1)
    assert mutated != source
    mutated += f"\n# direct-call decoy: {old.strip()}\n"

    assert not _game_lifecycle_contract(mutated, function_name, game)


@pytest.mark.parametrize(
    ("test_file", "function_name", "game", "later_lifecycle_anchor"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
            '        run_and_assert_ok(env, server_name, "status")\n',
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
            '        run_and_assert_ok(env, server_name, "status")\n',
        ),
    ),
)
def test_game_lifecycle_ast_contract_rejects_duplicate_or_reordered_start(
    test_file,
    function_name,
    game,
    later_lifecycle_anchor,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    start = '        run_and_assert_ok(env, server_name, "start")\n'
    assert source.count(start) == 1

    duplicate = source.replace(start, start + start, 1)
    moved = source.replace(start, "", 1).replace(
        later_lifecycle_anchor,
        later_lifecycle_anchor + start,
        1,
    )

    assert not _game_lifecycle_contract(duplicate, function_name, game)
    assert not _game_lifecycle_contract(moved, function_name, game)


@pytest.mark.parametrize(
    ("test_file", "function_name", "game"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
        ),
    ),
)
@pytest.mark.parametrize("location", ("before", "protected"))
@pytest.mark.parametrize(
    "escape_statement",
    (
        'pytest.skip("bypass")',
        'pytest.xfail("bypass")',
        'raise RuntimeError("bypass")',
        "return",
    ),
)
def test_game_lifecycle_ast_contract_rejects_unconditional_escapes(
    test_file,
    function_name,
    game,
    location,
    escape_statement,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    if location == "before":
        anchor = "    # create\n"
        replacement = f"    {escape_statement}\n" + anchor
    else:
        anchor = '        run_and_assert_ok(env, server_name, "start")\n'
        replacement = f"        {escape_statement}\n" + anchor
    mutated = source.replace(anchor, replacement, 1)
    assert mutated != source

    assert not _game_lifecycle_contract(mutated, function_name, game)


@pytest.mark.parametrize(
    ("test_file", "function_name", "game"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
        ),
    ),
)
@pytest.mark.parametrize(
    "weakened_start",
    (
        '        if True:\n            run_and_assert_ok(env, server_name, "start")\n',
        '        for _unused in (None,):\n            run_and_assert_ok(env, server_name, "start")\n',
        (
            "        def start_server():\n"
            '            run_and_assert_ok(env, server_name, "start")\n'
            "        start_server()\n"
        ),
    ),
)
def test_game_lifecycle_ast_contract_rejects_wrapped_start(
    test_file,
    function_name,
    game,
    weakened_start,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    start = '        run_and_assert_ok(env, server_name, "start")\n'
    mutated = source.replace(start, weakened_start, 1)
    assert mutated != source

    assert not _game_lifecycle_contract(mutated, function_name, game)


@pytest.mark.parametrize(
    ("test_file", "function_name", "game"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
        ),
    ),
)
@pytest.mark.parametrize(
    ("old", "new"),
    (
        (
            "    run_and_assert_ok,\n",
            "    run_and_assert_ok as lifecycle_runner,\n",
        ),
        (
            "    capture_alphagsm_stop,\n",
            "    capture_alphagsm_stop as stop_runner,\n",
        ),
        ("import pytest\n", "import pytest as test_api\n"),
    ),
)
def test_game_lifecycle_ast_contract_requires_exact_trusted_imports(
    test_file,
    function_name,
    game,
    old,
    new,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    mutated = source.replace(old, new, 1)
    assert mutated != source

    assert not _game_lifecycle_contract(mutated, function_name, game)


@pytest.mark.parametrize(
    ("test_file", "function_name", "game"),
    (
        (
            "test_returntomoriaserver.py",
            "test_returntomoriaserver_lifecycle",
            "moria",
        ),
        (
            "test_theforestserver.py",
            "test_theforestserver_lifecycle",
            "forest",
        ),
    ),
)
@pytest.mark.parametrize(
    "binding",
    (
        "run_and_assert_ok = replacement_runner",
        "capture_alphagsm_stop = replacement_stop",
        "pytest = replacement_pytest",
        "lifecycle_runner = run_and_assert_ok",
        "stop_runner = capture_alphagsm_stop",
        "test_api = pytest",
    ),
)
def test_game_lifecycle_ast_contract_rejects_rebinding_and_alias_creation(
    test_file,
    function_name,
    game,
    binding,
):
    source_path = Path(__file__).parents[1] / "integration_tests" / test_file
    source = source_path.read_text(encoding="utf-8")
    function_anchor = f"def {function_name}(tmp_path):\n"
    mutated = source.replace(
        function_anchor,
        function_anchor + f"    {binding}\n",
        1,
    )
    assert mutated != source

    assert not _game_lifecycle_contract(mutated, function_name, game)


def test_forest_removes_obsolete_diagnostic_imports():
    source_path = (
        Path(__file__).parents[1]
        / "integration_tests"
        / "test_theforestserver.py"
    )
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    conftest_imports = {
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "conftest"
        for alias in node.names
    }

    assert not {"log_command_result", "run_alphagsm"} & conftest_imports
    assert "wait_for_udp_closed" in conftest_imports


def test_forest_lifecycle_guard_rejects_aliased_tcp_shutdown_decoy():
    source_path = (
        Path(__file__).parents[1]
        / "integration_tests"
        / "test_theforestserver.py"
    )
    source = source_path.read_text(encoding="utf-8")
    mutated = source.replace(
        "    wait_for_udp_closed,\n",
        "    wait_for_tcp_closed as wait_for_udp_closed,\n",
        1,
    )
    assert mutated != source

    assert not _game_lifecycle_contract(
        mutated,
        "test_theforestserver_lifecycle",
        "forest",
    )


def test_return_to_moria_info_readiness_requires_managed_port(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )

    source = inspect.getsource(moria_test.test_returntomoriaserver_lifecycle)

    assert _moria_info_readiness_contract(source)


def test_return_to_moria_status_candidates_prefer_current_path_and_keep_legacy(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )

    candidates = moria_test.status_json_candidates("/srv/moria")

    assert candidates == (
        Path("/srv/moria/Moria/Config/status.json"),
        Path("/srv/moria/Moria/Config/Status.json"),
        Path("/srv/moria/Moria/Saved/Config/status.json"),
        Path("/srv/moria/Moria/Saved/Config/Status.json"),
    )


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ('            "udp",', '            "tcp",'),
        ("            expected_port=port,", "            expected_port=port + 1,"),
        ("            expected_port=port,", "            # expected_port=port"),
    ),
)
def test_moria_info_ast_guard_rejects_protocol_port_and_comment_mutations(old, new):
    source_path = (
        Path(__file__).parents[1]
        / "integration_tests"
        / "test_returntomoriaserver.py"
    )
    source = source_path.read_text(encoding="utf-8")
    mutated = source.replace(old, new, 1)
    assert mutated != source

    assert not _moria_info_readiness_contract(mutated)


def test_moria_info_ast_guard_rejects_moved_readiness_order():
    source = """
def test_returntomoriaserver_lifecycle():
    info_data = wait_for_info_protocol(
        env,
        server_name,
        "udp",
        START_TIMEOUT,
        expected_port=port,
    )
    status_payload = wait_for_status_json_running(
        env,
        server_name,
        status_json_path,
        START_TIMEOUT,
    )
"""

    assert not _moria_info_readiness_contract(source)


@pytest.mark.parametrize(
    "readiness_body",
    (
        """
        if False:
            info_data = wait_for_info_protocol(
                env, server_name, "udp", START_TIMEOUT, expected_port=port
            )
        # info_data = wait_for_info_protocol(
        #     env, server_name, "udp", START_TIMEOUT, expected_port=port
        # )
""",
        """
        for _unused in ():
            info_data = wait_for_info_protocol(
                env, server_name, "udp", START_TIMEOUT, expected_port=port
            )
""",
        """
        def unused_readiness():
            return wait_for_info_protocol(
                env, server_name, "udp", START_TIMEOUT, expected_port=port
            )
""",
    ),
)
def test_moria_info_ast_guard_rejects_nested_unreachable_and_comment_decoys(
    readiness_body,
):
    source = f"""
def test_returntomoriaserver_lifecycle():
    try:
        status_payload = wait_for_status_json_running(
            env, server_name, status_json_path, START_TIMEOUT
        )
{readiness_body}
    finally:
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1]
        )
    assert_alphagsm_result_ok(stop_result)
"""

    assert not _moria_info_readiness_contract(source)


def test_return_to_moria_safe_status_uses_allowlisted_projection(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )

    source = inspect.getsource(moria_test._safe_status_diagnostics)

    assert _safe_moria_status_contract(source)


@pytest.mark.parametrize(
    "source",
    (
        """
# def _safe_status_diagnostics(payload):
def renamed_safe_status(payload):
    return {
        field: payload[field]
        for field in _SAFE_STATUS_DIAGNOSTIC_FIELDS
        if field in payload
    }
""",
        """
def _safe_status_diagnostics(payload):
    return payload
""",
    ),
)
def test_safe_status_ast_guard_rejects_rename_comment_and_raw_return(source):
    assert not _safe_moria_status_contract(source)


@pytest.mark.parametrize(
    "unsafe_statement",
    (
        "    if include_secrets:\n        return payload\n",
        "    if False:\n        return payload\n",
        "    value = payload if include_secrets else {}\n",
    ),
)
def test_safe_status_ast_guard_rejects_conditional_raw_or_unsafe_branches(
    unsafe_statement,
):
    source = """
def _safe_status_diagnostics(payload):
    if not isinstance(payload, dict):
        return None
""" + unsafe_statement + """
    return {
        field: payload[field]
        for field in _SAFE_STATUS_DIAGNOSTIC_FIELDS
        if field in payload
    }
"""

    assert not _safe_moria_status_contract(source)


def test_safe_status_ast_guard_rejects_unrelated_type_guard():
    source = """
def _safe_status_diagnostics(payload):
    if expose_secrets:
        return None
    return {
        field: payload[field]
        for field in _SAFE_STATUS_DIAGNOSTIC_FIELDS
        if field in payload
    }
"""

    assert not _safe_moria_status_contract(source)


def test_return_to_moria_status_timeout_reports_only_safe_payload_fields(
    monkeypatch,
    tmp_path,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    status_path = tmp_path / "Status.json"
    invite_code = "synthetic-invite-code-secret"
    join_code = "synthetic-join-code-secret"
    status_path.write_text(
        json.dumps(
            {
                "Status": "starting",
                "AdvertisedAddressAndPort": "127.0.0.1:7777",
                "InviteCode": invite_code,
                "JoinCode": join_code,
            }
        ),
        encoding="utf-8",
    )
    dumped_runtime = []

    monkeypatch.setattr(moria_test.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(moria_test.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda actual_env, server_name: dumped_runtime.append(
            (actual_env, server_name)
        ),
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        moria_test.wait_for_status_json_running(
            env,
            "itreturntomo",
            status_path,
            5,
        )

    failure_text = str(failure.value)
    captured = capsys.readouterr().out
    assert dumped_runtime == [(env, "itreturntomo")]
    assert "'Status': 'starting'" in failure_text
    assert "'AdvertisedAddressAndPort': '127.0.0.1:7777'" in failure_text
    assert "InviteCode" not in failure_text
    assert invite_code not in failure_text
    assert join_code not in failure_text
    assert invite_code not in captured
    assert join_code not in captured


def test_return_to_moria_status_running_returns_only_safe_payload_fields(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )
    invite_code = "synthetic-running-invite-secret"
    join_code = "synthetic-running-join-secret"
    status_path = tmp_path / "Status.json"
    status_path.write_text(
        json.dumps(
            {
                "Status": "running",
                "AdvertisedAddressAndPort": "127.0.0.1:7777",
                "InviteCode": invite_code,
                "JoinCode": join_code,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(moria_test.time, "time", _retaining_clock(0.0, 0.0))

    status = moria_test.wait_for_status_json_running(
        {},
        "itreturntomo",
        status_path,
        5,
    )

    assert status == {
        "Status": "running",
        "AdvertisedAddressAndPort": "127.0.0.1:7777",
    }
    assert invite_code not in repr(status)
    assert join_code not in repr(status)


def test_return_to_moria_status_running_accepts_upstream_lowercase_filename(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )
    status_path = tmp_path / "Moria" / "Config" / "status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        json.dumps(
            {
                "Status": "running",
                "AdvertisedAddressAndPort": "127.0.0.1:7777",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(moria_test.time, "time", _retaining_clock(0.0, 0.0))

    status = moria_test.wait_for_status_json_running(
        {},
        "itreturntomo",
        moria_test.status_json_candidates(tmp_path),
        5,
    )

    assert status["Status"] == "running"


def test_return_to_moria_status_timeout_clears_env_from_traceback(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    moria_test = importlib.import_module(
        "tests.integration_tests.test_returntomoriaserver"
    )
    env_secret = "moria-status-env-secret"
    status_path = tmp_path / "Status.json"
    status_path.write_text('{"Status":"starting"}', encoding="utf-8")
    monkeypatch.setattr(moria_test.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(moria_test.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(pytest.fail.Exception) as failure:
        moria_test.wait_for_status_json_running(
            {"ADMIN_PASSWORD": env_secret},
            "itreturntomo",
            status_path,
            5,
        )

    traceback_locals = _owned_traceback_locals(
        failure.value,
        "wait_for_status_json_running",
        "fail_readiness_timeout",
    )
    assert env_secret not in traceback_locals


@pytest.mark.parametrize(
    ("logged_text", "secret"),
    (
        ('"InviteCode": "invite-json-secret"', "invite-json-secret"),
        ("join_code=join-snake-secret", "join-snake-secret"),
        ("JOIN-CODE join-kebab-secret", "join-kebab-secret"),
        ("--invite-code=invite-cli-secret", "invite-cli-secret"),
    ),
)
def test_redact_logged_text_masks_invite_and_join_code_formats(logged_text, secret):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert secret not in redacted
    assert "<redacted>" in redacted


@pytest.mark.parametrize(
    ("logged_text", "secret"),
    (
        (
            'payload="{\\"InviteCode\\":\\"escaped-invite-secret\\"}"',
            "escaped-invite-secret",
        ),
        (
            'payload="{\\"join_code\\":\\"escaped-join-secret\\"}"',
            "escaped-join-secret",
        ),
        (
            'payload="{\\"JOIN CODE\\":\\"escaped-spaced-secret\\"}"',
            "escaped-spaced-secret",
        ),
    ),
)
def test_redact_logged_text_masks_escaped_json_codes(logged_text, secret):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert secret not in redacted
    assert "<redacted>" in redacted


def test_redact_logged_text_preserves_unrelated_escaped_json():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    logged_text = 'payload="{\\"Status\\":\\"running\\"}" message=healthy'

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == logged_text


@pytest.mark.parametrize(
    ("logged_text", "expected"),
    (
        (
            r'{"InviteCode":"prefix\"suffix","Status":"running"}',
            r'{"InviteCode":"<redacted>","Status":"running"}',
        ),
        (
            r"payload={'join_code': 'prefix\'suffix', 'Status': 'running'}",
            r"payload={'join_code': '<redacted>', 'Status': 'running'}",
        ),
    ),
)
def test_redact_logged_text_consumes_escaped_quotes_without_suffix_leaks(
    logged_text,
    expected,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == expected
    assert "prefix" not in redacted
    assert "suffix" not in redacted


@pytest.mark.parametrize("delimiter_slashes", (1, 3))
def test_redact_logged_text_handles_embedded_and_doubly_escaped_json(
    delimiter_slashes,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    delimiter = "\\" * delimiter_slashes + '"'
    escaped_quote = "\\" * (2 * delimiter_slashes + 1) + '"'
    logged_text = (
        f"payload={delimiter}{{{delimiter}InviteCode{delimiter}:"
        f"{delimiter}prefix{escaped_quote}suffix{delimiter},"
        f"{delimiter}Status{delimiter}:{delimiter}running{delimiter}}}{delimiter}"
        " tail=healthy"
    )
    expected = (
        f"payload={delimiter}{{{delimiter}InviteCode{delimiter}:"
        f"{delimiter}<redacted>{delimiter},"
        f"{delimiter}Status{delimiter}:{delimiter}running{delimiter}}}{delimiter}"
        " tail=healthy"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == expected
    assert "prefix" not in redacted
    assert "suffix" not in redacted


def test_redact_logged_text_uses_exact_sensitive_key_boundaries():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    logged_text = (
        'tokenizer=value secretary="value" passwordless=yes '
        'status="running" token bucket initialized secret service ready '
        'password file loaded'
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == logged_text


@pytest.mark.parametrize(
    ("logged_text", "secret"),
    (
        (
            "AWS_SECRET_ACCESS_KEY=compound-access-secret",
            "compound-access-secret",
        ),
        (
            "DATABASE_PASSWORD_FILE=compound-password-secret",
            "compound-password-secret",
        ),
        (
            "--aws-secret-access-key cli-compound-secret",
            "cli-compound-secret",
        ),
        (
            r'payload={\"DATABASE_PASSWORD_FILE\":\"escaped-compound-secret\"}',
            "escaped-compound-secret",
        ),
    ),
)
def test_redact_logged_text_masks_standard_compound_sensitive_keys(
    logged_text,
    secret,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert secret not in redacted
    assert "<redacted>" in redacted


def test_compound_sensitive_keys_are_redacted_in_command_and_environment_repr():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    access_secret = "compound-command-access-secret"
    password_secret = "compound-environment-password-secret"

    command = helpers._redact_command_args(  # pylint: disable=protected-access
        ("--aws-secret-access-key", access_secret)
    )
    environment = helpers._SecretSafeEnvironment(  # pylint: disable=protected-access
        {"DATABASE_PASSWORD_FILE": password_secret}
    )
    exposed = repr(command) + repr(environment)

    assert access_secret not in exposed
    assert password_secret not in exposed
    assert exposed.count("<redacted>") == 2


@pytest.mark.parametrize(
    "key",
    (
        "SSH_PRIVATE_KEY",
        "ssh-private-key",
        "Authorization",
        "authorization_header",
        "PRIVATE_KEY",
    ),
)
def test_credential_and_authorization_keys_are_redacted_in_logged_text(key):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    secret = f"credential-{key.lower()}-secret"

    redacted = helpers._redact_logged_text(  # pylint: disable=protected-access
        f'{key}="{secret}"'
    )

    assert secret not in redacted
    assert redacted.endswith('"<redacted>"')


@pytest.mark.parametrize("delimiter_slashes", (1, 3))
def test_credential_keys_are_redacted_in_escaped_json_layers(delimiter_slashes):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    authorization_secret = "escaped-authorization-secret"
    private_key_secret = "escaped-private-key-secret"
    delimiter = "\\" * delimiter_slashes + '"'
    logged_text = (
        f"payload={delimiter}{{{delimiter}Authorization{delimiter}:"
        f"{delimiter}{authorization_secret}{delimiter},"
        f"{delimiter}SSH_PRIVATE_KEY{delimiter}:"
        f"{delimiter}{private_key_secret}{delimiter}}}{delimiter}"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert authorization_secret not in redacted
    assert private_key_secret not in redacted
    assert redacted.count("<redacted>") == 2


def test_credential_keys_are_redacted_in_command_and_environment_repr():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    command_secrets = (
        "command-private-key-secret",
        "command-authorization-secret",
    )
    environment_secrets = (
        "environment-private-key-secret",
        "environment-authorization-secret",
    )
    command = helpers._redact_command_args(  # pylint: disable=protected-access
        (
            "--ssh-private-key",
            command_secrets[0],
            "--authorization",
            command_secrets[1],
        )
    )
    environment = helpers._SecretSafeEnvironment(  # pylint: disable=protected-access
        {
            "PRIVATE_KEY": environment_secrets[0],
            "AUTHORIZATION_HEADER": environment_secrets[1],
        }
    )
    exposed = repr(command) + repr(environment)

    for secret in (*command_secrets, *environment_secrets):
        assert secret not in exposed
    assert exposed.count("<redacted>") == 4


def test_credential_key_classification_preserves_adjacent_prose():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    logged_text = (
        "authorization succeeded; private key rotation complete; "
        "authorization header normalized; private keys loaded"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == logged_text


@pytest.mark.parametrize("separator", (": ", "="))
def test_authorization_assignment_redacts_the_entire_unquoted_header_value(
    separator,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    credential = "private-material-123"

    redacted = helpers._redact_logged_text(  # pylint: disable=protected-access
        f"Authorization{separator}Bearer {credential}"
    )

    assert redacted == f"Authorization{separator}<redacted>"
    assert "Bearer" not in redacted
    assert credential not in redacted


@pytest.mark.parametrize("delimiter_slashes", (1, 3))
def test_authorization_assignment_redacts_escaped_unquoted_header_value(
    delimiter_slashes,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    credential = "escaped-private-material-123"
    delimiter = "\\" * delimiter_slashes + '"'
    logged_text = (
        f"payload={delimiter}{{{delimiter}Authorization{delimiter}:"
        f"Bearer {credential}}}{delimiter}"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == (
        f"payload={delimiter}{{{delimiter}Authorization{delimiter}:"
        f"{delimiter}<redacted>{delimiter}}}{delimiter}"
    )
    assert "Bearer" not in redacted
    assert credential not in redacted


@pytest.mark.parametrize(
    "key_type",
    ("PRIVATE KEY", "RSA PRIVATE KEY", "OPENSSH PRIVATE KEY"),
)
def test_private_key_assignment_redacts_complete_multiline_key_block(key_type):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    body = "private-body-line-1\nprivate-body-line-2"
    logged_text = (
        f"SSH_PRIVATE_KEY=-----BEGIN {key_type}-----\n"
        f"{body}\n"
        f"-----END {key_type}-----\n"
        "status=ready"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == "SSH_PRIVATE_KEY=<redacted>\nstatus=ready"
    assert body not in redacted
    assert "BEGIN" not in redacted
    assert "END" not in redacted


def test_private_key_assignment_redacts_block_starting_on_following_line():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    body = "following-line-private-body"
    logged_text = (
        "PRIVATE_KEY=\n"
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        f"{body}\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
        "status=ready"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == "PRIVATE_KEY=<redacted>\nstatus=ready"
    assert body not in redacted


def test_private_key_assignment_redacts_one_line_key_through_matching_end_marker():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    body = "one-line-private-body"
    logged_text = (
        "PRIVATE_KEY=-----BEGIN PRIVATE KEY----- "
        f"{body} "
        "-----END PRIVATE KEY----- status=ready"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == "PRIVATE_KEY=<redacted> status=ready"
    assert body not in redacted


def test_truncated_private_key_assignment_redacts_all_remaining_text():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    body = "truncated-private-body\nstill-private-body"
    logged_text = (
        "SSH_PRIVATE_KEY=-----BEGIN OPENSSH PRIVATE KEY-----\n"
        f"{body}"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == "SSH_PRIVATE_KEY=<redacted>"
    assert body not in redacted
    assert "BEGIN" not in redacted


def test_explicit_sensitive_assignment_redacts_through_end_of_line():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    logged_text = (
        "token=first-secret second-secret status=healthy\n"
        "ordinary status remains visible"
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted == "token=<redacted>\nordinary status remains visible"
    assert "first-secret" not in redacted
    assert "second-secret" not in redacted


def test_secret_safe_environment_redacts_nested_header_and_private_key_blocks():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    header_secret = "environment-header-secret"
    private_body = "environment-private-key-body"
    environment = helpers._SecretSafeEnvironment(  # pylint: disable=protected-access
        {
            "HTTP_HEADERS": f"Authorization: Bearer {header_secret}",
            "SSH_PRIVATE_KEY": (
                "-----BEGIN OPENSSH PRIVATE KEY-----\n"
                f"{private_body}\n"
                "-----END OPENSSH PRIVATE KEY-----"
            ),
            "STATUS": "ready",
        }
    )

    rendered = repr(environment)

    assert header_secret not in rendered
    assert private_body not in rendered
    assert "Bearer" not in rendered
    assert "'STATUS': 'ready'" in rendered


def test_command_redaction_masks_authorization_scheme_and_credential_to_option_boundary():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    credential = "command-authorization-secret"

    redacted = helpers._redact_command_args(  # pylint: disable=protected-access
        (
            "--authorization",
            "Bearer",
            credential,
            "--timeout",
            "30",
        )
    )

    assert redacted == (
        "--authorization",
        "<redacted>",
        "<redacted>",
        "--timeout",
        "30",
    )
    assert credential not in repr(redacted)


def test_command_redaction_fails_closed_for_authorization_without_option_boundary():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    credential = "ambiguous-command-authorization-secret"

    redacted = helpers._redact_command_args(  # pylint: disable=protected-access
        ("Authorization", "Bearer", credential, "possibly-related-tail")
    )

    assert redacted == (
        "Authorization",
        "<redacted>",
        "<redacted>",
        "<redacted>",
    )
    assert credential not in repr(redacted)


def test_format_logged_command_redacts_header_argument_without_masking_next_option():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    credential = "header-argument-secret"

    rendered = helpers._format_logged_command(  # pylint: disable=protected-access
        "curl",
        (
            "--header",
            f"Authorization: Bearer {credential}",
            "--url",
            "https://example.invalid/health",
        ),
    )

    assert rendered == (
        "curl --header Authorization: <redacted> "
        "--url https://example.invalid/health"
    )
    assert credential not in rendered


@pytest.mark.parametrize("scalar", (None, True, False, 0, -17, 3.25, 6.02e23))
def test_redact_logged_text_preserves_valid_json_for_sensitive_scalars(scalar):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    logged_text = json.dumps(
        {"token": scalar, "status": "running"},
        separators=(",", ":"),
    )

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access
    payload = json.loads(redacted)

    assert payload == {"token": "<redacted>", "status": "running"}


@pytest.mark.parametrize(
    "logged_text",
    (
        "adminpassword=admin-secret",
        "rconpassword=rcon-secret",
        "api_key=api-secret",
        "licensekey=license-secret",
        "invite_code=invite-secret",
        "join-code=join-secret",
        "--api-key=cli-api-secret",
        "--rcon-password cli-rcon-secret",
    ),
)
def test_redact_logged_text_catches_exact_sensitive_key_families(logged_text):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(logged_text)  # pylint: disable=protected-access

    assert redacted.endswith("<redacted>")
    assert "-secret" not in redacted


@pytest.mark.parametrize("use_glob_wait", (False, True))
def test_log_marker_timeout_redacts_local_log_tails(
    monkeypatch,
    tmp_path,
    capsys,
    use_glob_wait,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "forest-invite-secret"
    join_code = "forest-join-secret"
    log_path = tmp_path / "connection.log"
    log_path.write_text(
        f'InviteCode={invite_code}\n"JoinCode": "{join_code}"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(helpers.time, "time", _retaining_clock(0.0, 0.0, 10.0))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    with pytest.raises(pytest.fail.Exception):
        if use_glob_wait:
            helpers.wait_for_glob_log_marker(
                tmp_path,
                "*.log",
                ["ready"],
                5,
            )
        else:
            helpers.wait_for_log_marker(log_path, ["ready"], 5)

    captured = capsys.readouterr().out
    assert invite_code not in captured
    assert join_code not in captured
    assert captured.count("<redacted>") >= 2


def test_wait_for_runtime_log_marker_returns_stdout_marker(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    calls = []
    timestamps = iter((0.0, 0.0))
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=0,
        stdout="booting\nserver ready\n",
        stderr="",
    )

    def _run_alphagsm(actual_env, *args, timeout):
        calls.append((actual_env, args, timeout))
        return result

    def _fake_clock():
        return next(timestamps)

    monkeypatch.setattr(helpers.time, "time", _fake_clock)
    monkeypatch.setattr(helpers.time, "monotonic", _fake_clock)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)

    collected = helpers.wait_for_runtime_log_marker(
        env,
        "ittestserver",
        ["server ready"],
        30,
    )

    assert collected == "booting\nserver ready\n"
    assert calls == [(env, ("ittestserver", "logs", "-n", "10000"), 30)]


def test_wait_for_runtime_log_marker_returns_only_redacted_collected_text(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "runtime-return-invite-secret"
    join_code = "runtime-return-join-secret"
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=0,
        stdout=f"server ready InviteCode={invite_code}",
        stderr=f'{{"JoinCode":"{join_code}"}}',
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)

    collected = helpers.wait_for_runtime_log_marker(
        {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
        "ittestserver",
        ["server ready"],
        30,
    )

    assert invite_code not in collected
    assert join_code not in collected
    assert "server ready" in collected
    assert collected.count("<redacted>") == 2


def test_wait_for_runtime_log_marker_bounds_poll_timeout_to_remaining_deadline(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=0,
        stdout="server ready",
        stderr="",
    )
    poll_timeouts = []
    timestamps = iter((10.0, 10.2))

    def _fake_clock():
        return next(timestamps)

    def _run_alphagsm(*args, timeout):
        poll_timeouts.append(timeout)
        return result

    monkeypatch.setattr(helpers.time, "time", _fake_clock)
    monkeypatch.setattr(helpers.time, "monotonic", _fake_clock)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)

    helpers.wait_for_runtime_log_marker(
        {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
        "ittestserver",
        ["server ready"],
        0.5,
    )

    assert poll_timeouts == [pytest.approx(0.3)]


def test_wait_for_runtime_log_marker_bounds_sleep_and_stops_at_deadline(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    failure = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=1,
        stdout="still starting",
        stderr="",
    )
    timestamps = iter((0.0, 0.0, 0.6, 1.0))
    attempts = []
    sleeps = []

    def _run_alphagsm(*args, **kwargs):
        attempts.append((args, kwargs))
        return failure

    monkeypatch.setattr(helpers.time, "monotonic", lambda: next(timestamps))
    monkeypatch.setattr(helpers.time, "sleep", sleeps.append)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(helpers, "_dump_alphagsm_runtime_logs", lambda *args: None)

    with pytest.raises(
        pytest.fail.Exception,
        match="Runtime logs never showed readiness markers",
    ):
        helpers.wait_for_runtime_log_marker(
            {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            "ittestserver",
            ["ready"],
            1,
        )

    assert sleeps == [pytest.approx(0.4)]
    assert len(attempts) == 1


def test_wait_for_runtime_log_marker_returns_stderr_marker(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=0,
        stdout="",
        stderr="runtime ready on stderr\n",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: result)

    collected = helpers.wait_for_runtime_log_marker(
        {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
        "ittestserver",
        ["ready on stderr"],
        30,
    )

    assert collected == "runtime ready on stderr\n"


def test_wait_for_runtime_log_marker_retries_failed_and_empty_polls(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    polls = iter(
        (
            subprocess.CompletedProcess(
                args=["alphagsm"],
                returncode=1,
                stdout="ready but command failed",
                stderr="failure",
            ),
            subprocess.TimeoutExpired(["alphagsm"], timeout=120),
            subprocess.CompletedProcess(
                args=["alphagsm"],
                returncode=0,
                stdout="still starting",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["alphagsm"],
                returncode=0,
                stdout="startup complete",
                stderr="runtime ready",
            ),
        )
    )
    attempts = []

    def _run_alphagsm(*args, **kwargs):
        attempts.append((args, kwargs))
        outcome = next(polls)
        if isinstance(outcome, subprocess.TimeoutExpired):
            raise outcome
        return outcome

    timestamps = iter((0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0))

    def _fake_clock():
        return next(timestamps)

    monkeypatch.setattr(helpers.time, "time", _fake_clock)
    monkeypatch.setattr(helpers.time, "monotonic", _fake_clock)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)

    collected = helpers.wait_for_runtime_log_marker(
        {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
        "ittestserver",
        ["runtime ready"],
        30,
    )

    assert collected == "startup complete\nruntime ready"
    assert len(attempts) == 4


def test_wait_for_runtime_log_marker_logs_last_poll_before_terminal_diagnostics(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    last_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "logs"],
        returncode=1,
        stdout="last stdout",
        stderr="last stderr",
    )
    events = []
    timestamps = iter((0.0, 0.0, 10.0))

    def _fake_clock():
        return next(timestamps)

    monkeypatch.setattr(helpers.time, "time", _fake_clock)
    monkeypatch.setattr(helpers.time, "monotonic", _fake_clock)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: last_result)
    monkeypatch.setattr(
        helpers,
        "log_command_result",
        lambda name, result, **kwargs: events.append(("last-poll", result)),
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda actual_env, server_name, lines=200: events.append(
            ("runtime-dump", actual_env, server_name, lines)
        ),
    )

    with pytest.raises(
        pytest.fail.Exception,
        match="Runtime logs never showed readiness markers",
    ):
        helpers.wait_for_runtime_log_marker(
            env,
            "ittestserver",
            ["ready"],
            5,
        )

    assert events[0][0] == "last-poll"
    logged_result = events[0][1]
    assert logged_result.args == last_result.args
    assert logged_result.returncode == last_result.returncode
    assert logged_result.stdout == last_result.stdout
    assert logged_result.stderr == last_result.stderr
    assert events[1] == ("runtime-dump", env, "ittestserver", 200)


def test_wait_for_runtime_log_marker_decodes_and_redacts_timeout_bytes(
    monkeypatch,
    capsys,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    timeout_error = subprocess.TimeoutExpired(
        ["alphagsm", "ittestserver", "logs"],
        timeout=1,
        output=b"token=abc123\ninvalid=\xff",
        stderr=b"password=hunter2",
    )
    timestamps = iter((0.0, 0.0, 10.0))

    def _fake_clock():
        return next(timestamps)

    def _run_alphagsm(*args, **kwargs):
        raise timeout_error

    monkeypatch.setattr(helpers.time, "time", _fake_clock)
    monkeypatch.setattr(helpers.time, "monotonic", _fake_clock)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)
    monkeypatch.setattr(helpers, "_dump_alphagsm_runtime_logs", lambda *args: None)

    with pytest.raises(
        pytest.fail.Exception,
        match="Runtime logs never showed readiness markers",
    ):
        helpers.wait_for_runtime_log_marker(
            {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
            "ittestserver",
            ["ready"],
            5,
        )

    captured = capsys.readouterr().out
    assert "abc123" not in captured
    assert "hunter2" not in captured
    assert captured.count("<redacted>") == 2
    assert "\ufffd" in captured


def test_wait_for_info_protocol_retries_matching_protocol_on_wrong_port(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    results = iter(
        (
            subprocess.CompletedProcess(
                args=["alphagsm"],
                returncode=0,
                stdout='{"protocol": "udp", "port": 27015}',
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["alphagsm"],
                returncode=0,
                stdout='{"protocol": "udp", "port": 27016}',
                stderr="",
            ),
        )
    )
    attempts = []
    timestamps = iter((0.0, 0.0, 1.0))

    def _run_alphagsm(*args, **kwargs):
        attempts.append((args, kwargs))
        return next(results)

    monkeypatch.setattr(helpers.time, "time", lambda: next(timestamps))
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(helpers, "run_alphagsm", _run_alphagsm)

    payload = helpers.wait_for_info_protocol(
        {"ALPHAGSM_CONFIG_LOCATION": "dummy"},
        "ittestserver",
        "udp",
        5,
        expected_port="27016",
    )

    assert payload == {"protocol": "udp", "port": 27016}
    assert len(attempts) == 2


def test_run_and_assert_ok_dumps_runtime_logs_for_failed_lifecycle_command(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    failure = subprocess.CompletedProcess(
        args=["alphagsm", "itreturntomo", "query"],
        returncode=1,
        stdout="",
        stderr="Server does not appear to be responding",
    )
    env = {"ALPHAGSM_CONFIG_LOCATION": "dummy"}
    dumped_runtime = []

    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: failure)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "skip_for_known_steamcmd_issue",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        helpers,
        "_dump_alphagsm_runtime_logs",
        lambda actual_env, server_name, lines=200: dumped_runtime.append(
            (actual_env, server_name, lines)
        ),
    )

    with pytest.raises(AssertionError, match="does not appear to be responding"):
        helpers.run_and_assert_ok(env, "itreturntomo", "query")

    assert dumped_runtime == [(env, "itreturntomo", 200)]


def test_build_integration_tmp_path_uses_work_dir(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(tmp_path))

    class _Factory:
        def mktemp(self, name):
            raise AssertionError("mktemp should not be used when ALPHAGSM_WORK_DIR is set")

    result = helpers.build_integration_tmp_path("armarserver", _Factory())

    assert result.parent == tmp_path / "pytest-integration"
    assert result.name.startswith("armarserver-")
    assert result.is_dir()


def test_build_integration_tmp_path_uses_default_work_root(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("ALPHAGSM_WORK_DIR", raising=False)
    monkeypatch.setattr(helpers, "DEFAULT_INTEGRATION_WORK_DIR", tmp_path / "shared-work")

    class _Factory:
        def mktemp(self, name):
            raise AssertionError("mktemp should not be used when a default work root exists")

    result = helpers.build_integration_tmp_path("ndserver", _Factory())

    assert result.parent == tmp_path / "shared-work" / "pytest-integration"
    assert result.name.startswith("ndserver-")
    assert result.is_dir()


def test_format_logged_command_redacts_secret_set_values():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    rendered = helpers._format_logged_command(  # pylint: disable=protected-access
        "alphagsm",
        ("ittestlif", "set", "db_password", "hunter2"),
    )

    assert rendered == "alphagsm ittestlif set db_password <redacted>"


def test_format_logged_command_redacts_inline_secret_assignment_flags():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    rendered = helpers._format_logged_command(  # pylint: disable=protected-access
        "alphagsm",
        ("ittestlif", "start", "--db-password=hunter2", "token=abc123"),
    )

    assert rendered == "alphagsm ittestlif start --db-password=<redacted> token=<redacted>"


def test_redact_logged_text_masks_secret_values_in_common_output_shapes():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    redacted = helpers._redact_logged_text(  # pylint: disable=protected-access
        '\n'.join(
            (
                'db_password=hunter2',
                '"token": "abc123"',
                'rcon_password supersecret',
                '--db-password=hunter2',
            )
        )
    )

    assert "hunter2" not in redacted
    assert "abc123" not in redacted
    assert "supersecret" not in redacted
    assert redacted.count("<redacted>") >= 4


def test_log_command_result_redacts_secret_values_from_stdout_and_stderr(capsys):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=1,
        stdout='db_password=hunter2\n"token": "abc123"\n',
        stderr='rcon_password supersecret\n',
    )

    helpers.log_command_result(
        "alphagsm",
        result,
        command_args=("ittestlif", "set", "db_password", "hunter2"),
    )

    captured = capsys.readouterr().out
    assert "=== alphagsm ===" in captured
    assert "hunter2" not in captured
    assert "abc123" not in captured
    assert "supersecret" not in captured
    assert captured.count("<redacted>") >= 3


def test_write_config_keeps_downloads_inside_test_home_by_default(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"

    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(tmp_path / "shared-work"))
    monkeypatch.delenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", raising=False)

    helpers.write_config(config_path, home_dir)

    text = config_path.read_text(encoding="utf-8")
    assert f"db_path = {home_dir / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {home_dir / 'downloads' / 'downloads'}" in text
    assert "[runtime]" in text
    assert "backend = process" in text


def test_write_config_can_use_shared_download_cache_when_opted_in(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"
    shared_root = tmp_path / "shared-work"

    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(shared_root))
    monkeypatch.setenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", "1")

    helpers.write_config(config_path, home_dir)

    text = config_path.read_text(encoding="utf-8")
    assert f"db_path = {shared_root / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {shared_root / 'downloads' / 'downloads'}" in text
    assert "[runtime]" in text
    assert "backend = process" in text


def test_parse_recommended_port_overrides_reads_full_claim_set():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    parsed = helpers._parse_recommended_port_overrides(
        "Port conflicts detected\n"
        "Recommended free port set: port=42270 queryport=27016 peerport=27017\n"
    )

    assert parsed == {
        "port": 42270,
        "queryport": 27016,
        "peerport": 27017,
    }


def test_set_source_hibernation_preserves_line_boundaries_when_appending(tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    server_cfg = tmp_path / "server.cfg"
    server_cfg.write_text('hostname "AlphaGSM IOSoccer"', encoding="utf-8")

    helpers.set_source_hibernation(server_cfg, enabled=True)

    assert server_cfg.read_text(encoding="utf-8") == (
        'hostname "AlphaGSM IOSoccer"\n'
        "sv_hibernate_when_empty 1\n"
    )


def test_iosserver_hibernation_and_rewrite_sequence_keeps_lines_separate(tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    server_cfg = tmp_path / "server.cfg"
    server_cfg.write_text(
        'exec shared_server.cfg\n\nhostname "IOSoccer Dedicated Server"',
        encoding="utf-8",
    )

    helpers.set_source_hibernation(server_cfg, enabled=True)
    rewrite_space_config(
        server_cfg,
        {
            "hostname": '"AlphaGSM IOSoccer"',
            "rcon_password": '""',
            "sv_password": '""',
        },
    )

    assert server_cfg.read_text(encoding="utf-8") == (
        "exec shared_server.cfg\n"
        "\n"
        'hostname "AlphaGSM IOSoccer"\n'
        "sv_hibernate_when_empty 1\n"
        'rcon_password ""\n'
        'sv_password ""\n'
    )


def test_module_uses_explicit_docker_runtime_for_custom_test_module():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    assert helpers._module_uses_explicit_docker_runtime(  # pylint: disable=protected-access
        "portprobe",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )


def test_module_uses_explicit_docker_runtime_returns_false_when_module_load_fails(
    monkeypatch,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_load_runtime_module",
        lambda module_name, servermodulespackage="gamemodules.": (_ for _ in ()).throw(
            ImportError("boom")
        ),
    )

    assert not helpers._module_uses_explicit_docker_runtime("missing-module")  # pylint: disable=protected-access


def test_run_setup_with_port_retry_applies_recommended_nonprimary_claims(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")

    calls = []
    setup_failure = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=1,
        stdout="",
        stderr=(
            "Port conflicts detected:\n"
            "- unmanaged: Live listener already holds 0.0.0.0:27015\n"
            "Recommended free port set: port=42270 queryport=27016\n"
        ),
    )
    set_success = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=0,
        stdout="Value set\n",
        stderr="",
    )
    setup_success = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=0,
        stdout="Setup complete\n",
        stderr="",
    )
    responses = iter([setup_failure, set_success, setup_success])

    def _fake_run_alphagsm(env, *command_parts, timeout=None):
        calls.append(command_parts)
        return next(responses)

    monkeypatch.setattr(helpers, "run_alphagsm", _fake_run_alphagsm)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(helpers, "skip_for_known_steamcmd_issue", lambda result: None)
    monkeypatch.setattr(helpers, "pick_free_tcp_port", lambda: 49999)

    result, port = helpers.run_setup_with_port_retry(
        {"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
        "itblackwake",
        42267,
        tmp_path / "server",
    )

    assert result.returncode == 0
    assert port == 42270
    assert calls == [
        ("itblackwake", "setup", "-n", "42267", str(tmp_path / "server")),
        ("itblackwake", "set", "queryport", "27016"),
        ("itblackwake", "setup", "-n", "42270", str(tmp_path / "server")),
    ]


def test_run_setup_with_port_retry_forwards_known_steamcmd_flake_app_id(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    setup_failure = subprocess.CompletedProcess(
        args=["alphagsm"],
        returncode=3,
        stdout="Error! App '294420' state is 0x202 after update job.\n",
        stderr="",
    )

    monkeypatch.setattr(
        helpers,
        "run_alphagsm",
        lambda env, *command_parts, timeout=None: setup_failure,
    )
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(pytest.skip.Exception, match=r"app 294420"):
        helpers.run_setup_with_port_retry(
            {"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
            "it7dtd",
            26900,
            tmp_path / "server",
            steam_app_id=294420,
        )


def test_run_setup_with_port_retry_returns_sanitized_success_clone(
    monkeypatch,
    tmp_path,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    invite_code = "setup-success-invite-secret"
    raw_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "setup"],
        returncode=0,
        stdout=f"Setup complete InviteCode={invite_code}",
        stderr="",
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: raw_result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    returned, port = helpers.run_setup_with_port_retry(
        {},
        "ittestserver",
        27015,
        tmp_path / "server",
    )

    assert returned is not raw_result
    assert returned.returncode == 0
    assert invite_code not in returned.stdout
    assert returned.stdout.endswith("InviteCode=<redacted>")
    assert port == 27015


@pytest.mark.parametrize(
    ("known_skip", "expected_exception"),
    (
        (False, AssertionError),
        (True, pytest.skip.Exception),
    ),
)
def test_run_setup_with_port_retry_clears_raw_failure_and_skip_traceback_locals(
    monkeypatch,
    tmp_path,
    known_skip,
    expected_exception,
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    env_secret = "setup-traceback-env-secret"
    argument_secret = "setup-traceback-argument-secret"
    output_secret = "setup-traceback-output-secret"
    failure_prefix = "ENABLED (AUTH): provider required\n" if known_skip else ""
    raw_result = subprocess.CompletedProcess(
        args=["alphagsm", "ittestserver", "setup", "--join-code", argument_secret],
        returncode=1,
        stdout="",
        stderr=(
            f"{failure_prefix}AWS_SECRET_ACCESS_KEY={output_secret}\n"
        ),
    )
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *args, **kwargs: raw_result)
    monkeypatch.setattr(helpers, "log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(expected_exception) as failure:
        helpers.run_setup_with_port_retry(
            {"DATABASE_PASSWORD_FILE": env_secret},
            "ittestserver",
            27015,
            tmp_path / "server",
            "--join-code",
            argument_secret,
            max_tries=1,
        )

    exposed = str(failure.value) + _owned_traceback_locals(
        failure.value,
        "run_setup_with_port_retry",
    )
    assert env_secret not in exposed
    assert argument_secret not in exposed
    assert output_secret not in exposed


def test_backend_write_java_wrapper_prefers_java_home(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.backend_integration_tests.conftest")
    java_home = tmp_path / "jdk-25"
    java_bin = java_home / "bin"
    java_bin.mkdir(parents=True)
    java_path = java_bin / "java"
    java_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    java_path.chmod(0o755)
    wrapper_path = tmp_path / "java-wrapper.sh"

    monkeypatch.setenv("JAVA_HOME", str(java_home))
    monkeypatch.setattr(helpers.shutil, "which", lambda name: "/usr/bin/java")

    helpers._write_java_wrapper(wrapper_path, "-Xms256M", "-Xmx768M")

    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert str(java_path) in wrapper_text
    assert "/usr/bin/java" not in wrapper_text


def test_backend_write_java_wrapper_falls_back_to_path(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.backend_integration_tests.conftest")
    wrapper_path = tmp_path / "java-wrapper.sh"

    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.setattr(helpers.shutil, "which", lambda name: "/opt/java/bin/java")

    helpers._write_java_wrapper(wrapper_path, "-Xms256M", "-Xmx768M")

    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert "/opt/java/bin/java" in wrapper_text


def test_skip_for_known_steamcmd_issue_skips_only_for_missing_configuration_0x202():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_skips_for_known_bare_state_202_flake_app():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '232130' state is 0x202 after update job.",
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=232130)


def test_skip_for_known_steamcmd_issue_skips_for_sevendaystodie_bare_state_202_flake():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '294420' state is 0x202 after update job.",
        stderr="",
    )

    with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
        helpers.skip_for_known_steamcmd_issue(result, app_id=294420)


def test_skip_for_known_steamcmd_issue_skips_for_new_known_bare_state_202_flake_apps():
    helpers = importlib.import_module("tests.integration_tests.conftest")

    for app_id in (346680, 746200):
        result = types.SimpleNamespace(
            stdout=f"Error! App '{app_id}' state is 0x202 after update job.",
            stderr="",
        )

        with pytest.raises(pytest.skip.Exception, match="SteamCMD flake skip"):
            helpers.skip_for_known_steamcmd_issue(result, app_id=app_id)


def test_skip_for_known_steamcmd_issue_does_not_skip_other_steamcmd_failures():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! Timed out waiting for download chunks.",
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_does_not_skip_unknown_bare_state_202_app():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout="Error! App '317670' state is 0x202 after update job.",
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=317670)


def test_skip_for_known_steamcmd_issue_does_not_skip_when_app_id_does_not_match():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result, app_id=222860)


def test_skip_for_known_steamcmd_issue_does_not_skip_without_app_id():
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = types.SimpleNamespace(
        stdout=(
            "ERROR! Failed to install app '317670' (Missing configuration)\n"
            "Error! App '317670' state is 0x202 after update job."
        ),
        stderr="",
    )

    helpers.skip_for_known_steamcmd_issue(result)


@pytest.mark.parametrize("marker", ["ENABLED (BYO):", "ENABLED (AUTH):"])
def test_skip_for_known_steamcmd_issue_skips_for_supported_prerequisite_states(marker):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    result = subprocess.CompletedProcess(
        args=["steamcmd"],
        returncode=1,
        stdout="",
        stderr=f"Error running Command\n{marker} prerequisite not available in CI\n",
    )

    with pytest.raises(pytest.skip.Exception, match="Setup skipped"):
        helpers.skip_for_known_steamcmd_issue(result)


@pytest.mark.parametrize("escaped", (False, True))
def test_skip_for_known_steamcmd_issue_redacts_reason_and_traceback_locals(escaped):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    secret = "steamcmd-skip-invite-secret"
    if escaped:
        secret_text = (
            'payload="{\\"InviteCode\\":\\"prefix\\\\\\"'
            f'{secret}\\"}}"'
        )
    else:
        secret_text = f"InviteCode={secret}"
    result = subprocess.CompletedProcess(
        args=["steamcmd"],
        returncode=1,
        stdout="",
        stderr=f"ENABLED (AUTH): provider required\n{secret_text}\n",
    )

    with pytest.raises(pytest.skip.Exception) as failure:
        helpers.skip_for_known_steamcmd_issue(result)

    exposed = str(failure.value) + _owned_traceback_locals(
        failure.value,
        "skip_for_known_steamcmd_issue",
    )
    assert secret not in exposed
    assert "<redacted>" in exposed
