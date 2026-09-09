"""Static contract tests for integration test files."""

import ast
import re
import runpy
from pathlib import Path

import pytest


INTEGRATION_TEST_DIR = Path("tests/integration_tests")
DISABLED_SERVERS_PATH = Path("disabled_servers.conf")
SPECIAL_CASES = {"test_archive_backed_installs.py"}
SS14_INTEGRATION_TEST = INTEGRATION_TEST_DIR / "test_ss14server.py"
RUNTIME_AWARE_PROTOCOL_TESTS = {
    "test_arksurvivalascended.py": "source_rcon",
    "test_astroneerserver.py": "udp",
    "test_ns2server.py": "a2s",
    "test_ns2cserver.py": "a2s",
    "test_palworld.py": "udp",
    "test_bb2server.py": "a2s",
    "test_btserver.py": "udp",
    "test_cssserver.py": "a2s",
    "test_fofserver.py": "a2s",
    "test_gmodserver.py": "a2s",
    "test_insserver.py": "a2s",
    "test_l4d2server.py": "a2s",
    "test_pvkiiserver.py": "a2s",
    "test_rust.py": "a2s",
    "test_valheim.py": "udp",
    "test_sniperelite4server.py": "udp",
    "test_sonsoftheforestserver.py": "a2s",
    "test_ricochetserver.py": "a2s",
    "test_bmdmserver.py": "a2s",
    "test_empyrionserver.py": "tcp",
    "test_exfilserver.py": "tcp",
    "test_battlecryoffreedomserver.py": "tcp",
    "test_readyornotserver.py": "udp",
    "test_reignofdwarfserver.py": "tcp",
    "test_remnantsserver.py": "tcp",
    "test_sunkenlandserver.py": "tcp",
    "test_returntomoriaserver.py": "udp",
    "test_bdserver.py": "a2s",
    "test_blackops3server.py": "udp",
    "test_mythofempiresserver.py": "a2s",
    "test_nightingale.py": "http_status",
    "test_xntserver.py": "quake",
    "test_ahl2server.py": "tcp",
    "test_kf2server.py": "a2s",
    "test_unturned.py": "a2s",
}
STRICT_SOURCE_A2S_TESTS = (
    "test_bb2server.py",
    "test_bmdmserver.py",
    "test_bsserver.py",
    "test_ccserver.py",
    "test_cssserver.py",
    "test_dabserver.py",
    "test_dodsserver.py",
    "test_doiserver.py",
    "test_dysserver.py",
    "test_emserver.py",
    "test_fofserver.py",
    "test_gmodserver.py",
    "test_hl2dmserver.py",
    "test_hldmsserver.py",
    "test_insserver.py",
    "test_iosserver.py",
    "test_l4d2server.py",
    "test_l4dserver.py",
    "test_ndserver.py",
    "test_nmrihserver.py",
    "test_pvkiiserver.py",
    "test_tf2.py",
)
STRICT_GOLDSRC_A2S_TESTS = (
    "test_csczserver.py",
    "test_csserver.py",
    "test_dmcserver.py",
    "test_dodserver.py",
    "test_hldmserver.py",
    "test_opforserver.py",
    "test_tfcserver.py",
)
REQUIRED_TOP_LEVEL_IMPORTS = {
    "test_lifeisfeudalserver.py": (("subprocess", None),),
    "test_noonesurvivedserver.py": (
        ("effective_runtime_backend", "conftest"),
        ("require_proton", "conftest"),
    ),
    "test_notdserver.py": (
        ("effective_runtime_backend", "conftest"),
        ("require_proton", "conftest"),
    ),
    "test_outpostzeroserver.py": (("wait_for_info_protocol", "conftest"),),
}
WINE_PROTON_RUNTIME_TESTS = (
    "test_noonesurvivedserver.py",
    "test_notdserver.py",
)
CANONICAL_MODULE_IDS = {
    "test_terraria_vanilla.py": "terraria.vanilla",
    "test_satisfactory.py": "satisfactory",
}
RUNTIME_LOG_READINESS_TESTS = (
    "test_avserver.py",
    "test_btlserver.py",
    "test_btserver.py",
    "test_csczserver.py",
    "test_csserver.py",
    "test_dayofdragonsserver.py",
    "test_dmcserver.py",
    "test_dodserver.py",
    "test_hldmserver.py",
    "test_memoriesofmarsserver.py",
    "test_minecraft_paper.py",
    "test_minecraft_velocity.py",
    "test_mordserver.py",
    "test_necserver.py",
    "test_opforserver.py",
    "test_projectzomboid.py",
    "test_smallandserver.py",
    "test_tfcserver.py",
    "test_trackmaniaserver.py",
    "test_valheim.py",
    "test_bsserver.py",
    "test_ccserver.py",
    "test_dabserver.py",
    "test_dodsserver.py",
    "test_doiserver.py",
    "test_dysserver.py",
    "test_emserver.py",
    "test_hl2dmserver.py",
    "test_hldmsserver.py",
    "test_iosserver.py",
    "test_inssserver.py",
    "test_l4dserver.py",
    "test_ndserver.py",
    "test_nmrihserver.py",
    "test_svenserver.py",
    "test_tf2.py",
    "test_squad44server.py",
    "test_frozenflameserver.py",
    "test_minecraft_bungeecord.py",
    "test_minecraft_waterfall.py",
    "test_rimworldtogetherserver.py",
    "test_scpslserver.py",
    "test_wurmserver.py",
    "test_wfserver.py",
    "test_ut99server.py",
)


def _integration_test_files():
    return sorted(
        path
        for path in INTEGRATION_TEST_DIR.glob("test_*.py")
        if path.name not in SPECIAL_CASES
    )


def _disabled_module_names():
    names = []
    for raw_line in DISABLED_SERVERS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        names.append(line.split("\t", 1)[0].strip())
    return sorted(names)


def _top_level_imports(path):
    imports = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Import):
            imports.update(
                (alias.asname or alias.name.split(".", 1)[0], None)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports.update(
                (alias.asname or alias.name, node.module) for alias in node.names
            )
    return imports


def _call_name(call):
    if not isinstance(call, ast.Call):
        return None
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _call_argument(call, position, keyword):
    if len(call.args) > position:
        return call.args[position]
    return next(
        (item.value for item in call.keywords if item.arg == keyword),
        None,
    )


def _constant_value(node):
    return node.value if isinstance(node, ast.Constant) else None


def _mapping_key(node):
    if not isinstance(node, ast.Subscript):
        return None
    return _constant_value(node.slice)


def _test_function(tree):
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ),
        None,
    )


def _direct_assigned_call(statement):
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name) and isinstance(statement.value, ast.Call):
            return target.id, statement.value
    if (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and isinstance(statement.value, ast.Call)
    ):
        return statement.target.id, statement.value
    return None, None


def _direct_call(statement):
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return statement.value
    _target, call = _direct_assigned_call(statement)
    return call


def _alphagsm_command(call):
    if call is None or _call_name(call) not in {"run_and_assert_ok", "run_alphagsm"}:
        return None
    return _constant_value(_call_argument(call, 2, "command"))


def _call_has_argument(call, value):
    return any(_constant_value(argument) == value for argument in call.args)


def _is_exact_a2s_readiness(call):
    expected_port = _call_argument(call, 4, "expected_port")
    return (
        _call_name(call) == "wait_for_info_protocol"
        and _constant_value(_call_argument(call, 2, "expected_protocol")) == "a2s"
        and isinstance(expected_port, ast.Name)
        and expected_port.id == "port"
    )


def _protocol_expression(node):
    if isinstance(node, ast.Name) and "protocol" in node.id.lower():
        return True
    if _mapping_key(node) == "protocol":
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and bool(node.args)
        and _constant_value(node.args[0]) == "protocol"
    )


def _accepts_console_protocol(comparison):
    operands = [comparison.left, *comparison.comparators]
    has_protocol = any(
        _protocol_expression(node)
        for operand in operands
        for node in ast.walk(operand)
    )
    literal_protocols = {
        _constant_value(node)
        for operand in operands
        for node in ast.walk(operand)
        if _constant_value(node) in {"a2s", "console"}
    }
    exact_a2s = (
        len(comparison.ops) == 1
        and isinstance(comparison.ops[0], ast.Eq)
        and literal_protocols == {"a2s"}
    )
    return has_protocol and not exact_a2s


def _subscript_matches(node, variable_name, key):
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == variable_name
        and _mapping_key(node) == key
    )


def _has_exact_payload_assert(statements, variable_name, key, expected):
    return bool(
        _exact_payload_assert_indexes(statements, variable_name, key, expected)
    )


def _exact_payload_assert_indexes(statements, variable_name, key, expected):
    indexes = []
    for index, statement in enumerate(statements):
        if not isinstance(statement, ast.Assert):
            continue
        for comparison in ast.walk(statement.test):
            if (
                not isinstance(comparison, ast.Compare)
                or len(comparison.ops) != 1
                or not isinstance(comparison.ops[0], ast.Eq)
                or len(comparison.comparators) != 1
            ):
                continue
            left = comparison.left
            right = comparison.comparators[0]
            expected_left = (
                isinstance(left, ast.Name) and left.id == expected
                if expected == "port"
                else _constant_value(left) == expected
            )
            expected_right = (
                isinstance(right, ast.Name) and right.id == expected
                if expected == "port"
                else _constant_value(right) == expected
            )
            if _subscript_matches(left, variable_name, key) and expected_right:
                indexes.append(index)
                break
            if _subscript_matches(right, variable_name, key) and expected_left:
                indexes.append(index)
                break
    return indexes


def _target_contains_name(target, variable_name):
    return any(
        isinstance(node, ast.Name) and node.id == variable_name
        for node in ast.walk(target)
    )


def _statement_mutates_name(statement, variable_name):
    for node in ast.walk(statement):
        if isinstance(node, ast.Import) and any(
            (alias.asname or alias.name.split(".", 1)[0]) == variable_name
            for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and any(
            alias.name != "*"
            and (alias.asname or alias.name) == variable_name
            for alias in node.names
        ):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == variable_name:
                return True
        if isinstance(node, ast.arg) and node.arg == variable_name:
            return True
        if isinstance(node, ast.comprehension) and _target_contains_name(
            node.target, variable_name
        ):
            return True
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(_target_contains_name(target, variable_name) for target in targets):
                return True
        if isinstance(node, ast.NamedExpr) and _target_contains_name(
            node.target, variable_name
        ):
            return True
        if isinstance(node, (ast.For, ast.AsyncFor)) and _target_contains_name(
            node.target, variable_name
        ):
            return True
        if isinstance(node, (ast.With, ast.AsyncWith)) and any(
            item.optional_vars is not None
            and _target_contains_name(item.optional_vars, variable_name)
            for item in node.items
        ):
            return True
        if isinstance(node, ast.ExceptHandler) and node.name == variable_name:
            return True
        if isinstance(node, (ast.MatchAs, ast.MatchStar)):
            if node.name == variable_name:
                return True
        if isinstance(node, ast.MatchMapping) and node.rest == variable_name:
            return True
        if isinstance(node, ast.Delete) and any(
            _target_contains_name(target, variable_name) for target in node.targets
        ):
            return True
    return False


def _final_info_payload(try_body):
    result_calls = []
    for result_index, statement in enumerate(try_body):
        result_name, call = _direct_assigned_call(statement)
        if (
            not result_name
            or _alphagsm_command(call) != "info"
            or not _call_has_argument(call, "--json")
        ):
            continue
        result_calls.append((result_index, result_name))
    if result_calls:
        result_index, result_name = result_calls[-1]
        for payload_index in range(result_index + 1, len(try_body)):
            payload_name, payload_call = _direct_assigned_call(try_body[payload_index])
            if (
                payload_name
                and _call_name(payload_call) == "loads"
                and any(
                    isinstance(node, ast.Name) and node.id == result_name
                    for node in ast.walk(payload_call)
                )
            ):
                return result_index, payload_index, payload_name
        return result_index, None, None
    return None, None, None


def _direct_statement_contains_command(statement, command):
    if not isinstance(statement, (ast.Expr, ast.Assign, ast.AnnAssign)):
        return False
    return any(
        isinstance(node, ast.Call) and _alphagsm_command(node) == command
        for node in ast.walk(statement)
    )


def _assignment_names_and_call(statement):
    if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return [], None
    value = statement.value
    if not isinstance(value, ast.Call):
        return [], None
    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
    names = [
        node.id
        for target in targets
        for node in ast.walk(target)
        if isinstance(node, ast.Name)
    ]
    return names, value


def _asserts_successful_result(statement, result_name):
    if not isinstance(statement, ast.Assert):
        return False
    for comparison in ast.walk(statement.test):
        if (
            not isinstance(comparison, ast.Compare)
            or len(comparison.ops) != 1
            or not isinstance(comparison.ops[0], ast.Eq)
            or len(comparison.comparators) != 1
        ):
            continue
        operands = [comparison.left, comparison.comparators[0]]
        has_zero = any(_constant_value(operand) == 0 for operand in operands)
        has_returncode = any(
            isinstance(operand, ast.Attribute)
            and operand.attr == "returncode"
            and isinstance(operand.value, ast.Name)
            and operand.value.id == result_name
            for operand in operands
        )
        if has_zero and has_returncode:
            return True
    return False


def _asserts_successful_result_with_context(statement, result_name):
    if not _asserts_successful_result(statement, result_name):
        return False
    context_attributes = {
        node.attr
        for node in ast.walk(statement.msg)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == result_name
    } if statement.msg is not None else set()
    return {"stderr", "stdout"}.issubset(context_attributes)


def _captured_stop(main_try):
    for index, statement in enumerate(main_try.finalbody):
        result_name, call = _direct_assigned_call(statement)
        if (
            result_name
            and _call_name(call) == "run_alphagsm"
            and _alphagsm_command(call) == "stop"
        ):
            return index, result_name
    return None, None


def _pre_try_stage_violations(test_function, main_try, path):
    offenders = []
    try_index = test_function.body.index(main_try)
    pre_try = test_function.body[:try_index]
    stages = {"create": [], "setup": [], "start": []}
    for index, statement in enumerate(pre_try):
        call = _direct_call(statement)
        command = _alphagsm_command(call)
        if command in {"create", "setup", "start"}:
            stages[command].append((index, statement, call))
            continue
        _names, assigned_call = _assignment_names_and_call(statement)
        if _call_name(assigned_call) == "run_setup_with_port_retry":
            stages["setup"].append((index, statement, assigned_call))

    for stage in ("create", "setup", "start"):
        if not stages[stage]:
            offenders.append(f"{path}: missing {stage}")

    for stage in ("create", "start"):
        if stages[stage] and any(
            _call_name(call) != "run_and_assert_ok"
            for _index, _statement, call in stages[stage]
        ):
            offenders.append(f"{path}: {stage} must use run_and_assert_ok")

    if stages["setup"]:
        safe_setup = False
        for setup_index, statement, call in stages["setup"]:
            if _call_name(call) == "run_and_assert_ok":
                safe_setup = True
                continue
            result_names, _assigned_call = _assignment_names_and_call(statement)
            if any(
                _asserts_successful_result(later, result_name)
                for result_name in result_names
                for later in pre_try[setup_index + 1 :]
            ):
                safe_setup = True
        if not safe_setup:
            offenders.append(f"{path}: raw setup result must be asserted successful")

    if all(stages[stage] for stage in ("create", "setup", "start")):
        create_index = stages["create"][0][0]
        setup_index = stages["setup"][0][0]
        start_index = stages["start"][0][0]
        if not create_index < setup_index < start_index < try_index:
            offenders.append(
                f"{path}: create/setup/start must precede lifecycle try in order"
            )
    else:
        offenders.append(
            f"{path}: create/setup/start must precede lifecycle try in order"
        )
    return offenders


def _common_a2s_lifecycle_violations(tree, path):
    offenders = []
    test_function = _test_function(tree)
    if test_function is None:
        return [f"{path}: missing lifecycle test function"]

    main_try = next(
        (statement for statement in test_function.body if isinstance(statement, ast.Try)),
        None,
    )
    if main_try is None:
        return [
            f"{path}: missing lifecycle try/finally",
            f"{path}: missing create",
            f"{path}: missing setup",
            f"{path}: missing start",
            f"{path}: create/setup/start must precede lifecycle try in order",
            f"{path}: missing unconditional exact A2S info readiness",
            f"{path}: missing status",
            f"{path}: missing query",
            f"{path}: missing human-readable info",
            f"{path}: missing info --json",
            f"{path}: missing stop in finally",
            f"{path}: missing UDP shutdown verification",
        ]

    offenders.extend(_pre_try_stage_violations(test_function, main_try, path))

    for comparison in (
        node for node in ast.walk(test_function) if isinstance(node, ast.Compare)
    ):
        if _accepts_console_protocol(comparison):
            offenders.append(f"{path}: console protocol fallback")
            break

    readiness = []
    commands = {"status": [], "query": [], "info": [], "info-json": []}
    for index, statement in enumerate(main_try.body):
        _target, call = _direct_assigned_call(statement)
        if call is None:
            call = _direct_call(statement)
        if call is None:
            continue
        if _is_exact_a2s_readiness(call) and _direct_assigned_call(statement)[0]:
            readiness.append(index)
        command = _alphagsm_command(call)
        if command == "status":
            commands["status"].append((index, call))
        elif command == "query":
            commands["query"].append((index, call))
        elif command == "info" and _call_has_argument(call, "--json"):
            commands["info-json"].append((index, call))
        elif command == "info":
            commands["info"].append((index, call))

    if not readiness:
        offenders.append(f"{path}: missing unconditional exact A2S info readiness")
    lifecycle_checks = [
        index
        for command in ("query", "info", "info-json")
        for index, _call in commands[command]
    ]
    if readiness and lifecycle_checks and min(readiness) >= min(lifecycle_checks):
        offenders.append(f"{path}: A2S readiness follows query/info lifecycle checks")

    if (
        readiness
        and all(commands[key] for key in ("status", "query", "info", "info-json"))
    ):
        status_index = min(index for index, _call in commands["status"])
        query_index = min(index for index, _call in commands["query"])
        info_index = min(index for index, _call in commands["info"])
        info_json_index = min(index for index, _call in commands["info-json"])
        if not (
            min(readiness) < query_index
            and status_index < query_index < info_index < info_json_index
        ):
            offenders.append(f"{path}: lifecycle stages are out of order")

    readiness_boundary = min(readiness) if readiness else len(main_try.body)
    for statement in main_try.body[:readiness_boundary]:
        direct_exit = isinstance(statement, (ast.Return, ast.Raise))
        conditional_exit = isinstance(statement, ast.If) and any(
            isinstance(node, (ast.Return, ast.Raise)) for node in ast.walk(statement)
        )
        if direct_exit or conditional_exit:
            offenders.append(f"{path}: early exit before A2S readiness")
            break

    required_commands = (
        ("status", "status"),
        ("query", "query"),
        ("info", "human-readable info"),
        ("info-json", "info --json"),
    )
    for command_key, label in required_commands:
        if not commands[command_key]:
            offenders.append(f"{path}: missing {label}")
        elif any(
            _call_name(call) != "run_and_assert_ok"
            for _index, call in commands[command_key]
        ):
            offenders.append(f"{path}: {label} must use run_and_assert_ok")

    result_index, payload_index, payload_name = _final_info_payload(main_try.body)
    if result_index is not None and payload_index is not None:
        assertion_statements = main_try.body[payload_index + 1 :]
        protocol_assertions = _exact_payload_assert_indexes(
            assertion_statements, payload_name, "protocol", "a2s"
        )
        port_assertions = _exact_payload_assert_indexes(
            assertion_statements, payload_name, "port", "port"
        )
        last_assertion = max(protocol_assertions + port_assertions, default=-1)
        if any(
            _statement_mutates_name(statement, payload_name)
            for statement in assertion_statements[: last_assertion + 1]
        ):
            offenders.append(
                f"{path}: final info JSON payload mutated before assertions"
            )
        if not _has_exact_payload_assert(
            assertion_statements, payload_name, "protocol", "a2s"
        ):
            offenders.append(
                f"{path}: final info JSON lacks exact A2S protocol assertion"
            )
        if not _has_exact_payload_assert(
            assertion_statements, payload_name, "port", "port"
        ):
            offenders.append(f"{path}: final info JSON lacks exact port assertion")
    else:
        offenders.append(f"{path}: final info JSON lacks exact A2S protocol assertion")
        offenders.append(f"{path}: final info JSON lacks exact port assertion")

    stop_index, stop_result_name = _captured_stop(main_try)
    if stop_result_name is None:
        offenders.append(f"{path}: stop must be captured in finally")
    if not any(
        _direct_statement_contains_command(statement, "stop")
        for statement in main_try.finalbody
    ):
        offenders.append(f"{path}: missing stop in finally")
    if stop_result_name is not None and not any(
        index > stop_index
        and _call_name(_direct_call(statement)) == "log_command_result"
        and any(
            isinstance(node, ast.Name) and node.id == stop_result_name
            for node in ast.walk(statement)
        )
        for index, statement in enumerate(main_try.finalbody)
    ):
        offenders.append(f"{path}: stop result must be logged in finally")

    try_index = test_function.body.index(main_try)
    after_try = test_function.body[try_index + 1 :]
    stop_assertions = [
        index
        for index, statement in enumerate(after_try)
        if stop_result_name is not None
        and _asserts_successful_result_with_context(statement, stop_result_name)
    ]
    if not stop_assertions:
        offenders.append(
            f"{path}: stop result must be asserted successful after finally"
        )
    shutdown_indexes = [
        index
        for index, statement in enumerate(after_try)
        if _call_name(_direct_call(statement)) == "wait_for_udp_closed"
    ]
    if not shutdown_indexes:
        offenders.append(f"{path}: missing UDP shutdown verification")
    elif not stop_assertions or min(shutdown_indexes) <= min(stop_assertions):
        offenders.append(
            f"{path}: UDP shutdown verification must follow stop assertion"
        )
    return offenders


def _strict_source_a2s_violations(tree, path):
    offenders = _common_a2s_lifecycle_violations(tree, path)
    test_function = _test_function(tree)
    if test_function is None:
        return offenders

    all_calls = [node for node in ast.walk(test_function) if isinstance(node, ast.Call)]
    hibernation_calls = [
        call
        for call in all_calls
        if (_call_name(call) or "").endswith("_hibernation")
    ]
    if len(hibernation_calls) != 1:
        offenders.append(f"{path}: expected exactly one hibernation call")
    if any(
        _constant_value(_call_argument(call, 1, "enabled")) is not False
        for call in hibernation_calls
    ):
        offenders.append(f"{path}: hibernation must use literal enabled=False")

    main_try = next(
        (statement for statement in test_function.body if isinstance(statement, ast.Try)),
        None,
    )
    common_sequences = [test_function.body]
    if main_try is not None:
        common_sequences.append(main_try.body)
    ordered = False
    for statements in common_sequences:
        direct_calls = [_direct_call(statement) for statement in statements]
        hibernation_indexes = [
            index
            for index, call in enumerate(direct_calls)
            if call is not None and (_call_name(call) or "").endswith("_hibernation")
        ]
        start_indexes = [
            index
            for index, call in enumerate(direct_calls)
            if _alphagsm_command(call) == "start"
        ]
        if (
            len(hibernation_indexes) == 1
            and len(start_indexes) == 1
            and hibernation_indexes[0] < start_indexes[0]
        ):
            ordered = True
    if not ordered:
        offenders.append(f"{path}: hibernation must precede start on the common path")
    return offenders


def _sven_goldsrc_violations(tree, path):
    offenders = _common_a2s_lifecycle_violations(tree, path)
    forbidden_names = {"find_source_server_cfg", "set_source_hibernation"}
    imported_forbidden = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "conftest"
        for alias in node.names
        if alias.name in forbidden_names
    }
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    if imported_forbidden or any(
        _call_name(call) in forbidden_names | imported_forbidden
        or (_call_name(call) or "").endswith("_hibernation")
        for call in calls
    ):
        offenders.append(f"{path}: Source hibernation API is forbidden")

    test_function = _test_function(tree)
    main_try = next(
        (
            statement
            for statement in (test_function.body if test_function else [])
            if isinstance(statement, ast.Try)
        ),
        None,
    )
    if main_try is None:
        offenders.append(f"{path}: missing direct raw A2S validation")
        return offenders
    direct_raw_a2s = [
        index
        for index, statement in enumerate(main_try.body)
        if _call_name(_direct_call(statement)) == "wait_for_a2s_ready"
    ]
    query_info_indexes = [
        index
        for index, statement in enumerate(main_try.body)
        if _alphagsm_command(_direct_call(statement)) in {"query", "info"}
    ]
    if not direct_raw_a2s or (
        query_info_indexes and min(direct_raw_a2s) >= min(query_info_indexes)
    ):
        offenders.append(f"{path}: missing direct raw A2S validation")
    return offenders


def _has_common_runtime_log_readiness(tree):
    test_function = _test_function(tree)
    main_try = next(
        (
            statement
            for statement in (test_function.body if test_function else [])
            if isinstance(statement, ast.Try)
        ),
        None,
    )
    return main_try is not None and any(
        _call_name(_direct_call(statement)) == "wait_for_runtime_log_marker"
        for statement in main_try.body
    )


STRICT_SOURCE_FIXTURE = """
def test_server_lifecycle():
    port = 27015
    run_and_assert_ok(env, server_name, "create", module_name)
    setup_result = run_and_assert_ok(env, server_name, "setup")
    set_source_hibernation(server_cfg_path, enabled=False)
    run_and_assert_ok(env, server_name, "start")
    try:
        run_and_assert_ok(env, server_name, "status")
        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        query_result = run_and_assert_ok(env, server_name, "query")
        info_result = run_and_assert_ok(env, server_name, "info")
        info_json_result = run_and_assert_ok(
            env, server_name, "info", "--json"
        )
        final_info = json.loads(info_json_result.stdout.strip())
        assert final_info["protocol"] == "a2s"
        assert final_info["port"] == port
    finally:
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)
    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
"""


def _lifecycle_create_module_id(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lifecycle = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.endswith("_lifecycle")
        ),
        None,
    )
    if lifecycle is None:
        return None

    direct_literals = {
        target.id: statement.value.value
        for statement in lifecycle.body
        if isinstance(statement, ast.Assign)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
        for target in statement.targets
        if isinstance(target, ast.Name)
    }
    for node in ast.walk(lifecycle):
        if not isinstance(node, ast.Call) or len(node.args) < 4:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "run_and_assert_ok":
            continue
        if not isinstance(node.args[2], ast.Constant) or node.args[2].value != "create":
            continue
        module_argument = node.args[3]
        if isinstance(module_argument, ast.Constant):
            return module_argument.value
        if isinstance(module_argument, ast.Name):
            return direct_literals.get(module_argument.id)
    return None


def _resolved_path_parts(node, assignments, seen=None):
    if seen is None:
        seen = set()

    names = set()
    strings = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
            if child.id in assignments and child.id not in seen:
                nested_names, nested_strings = _resolved_path_parts(
                    assignments[child.id],
                    assignments,
                    seen | {child.id},
                )
                names.update(nested_names)
                strings.update(nested_strings)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            strings.add(child.value)
    return names, strings


def _resolves_to_manager_log_path(node, assignments):
    names, strings = _resolved_path_parts(node, assignments)
    return "logs" in strings and "install_dir" not in names


class _ManagerLogReadinessVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []
        self.assignments = [{}]
        self.wait_function_names = {"wait_for_log_marker"}

    def _visit_function(self, node):
        self.assignments.append(dict(self.assignments[-1]))
        for statement in node.body:
            self.visit(statement)
        self.assignments.pop()

    def visit_FunctionDef(self, node):  # pylint: disable=invalid-name
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):  # pylint: disable=invalid-name
        self._visit_function(node)

    def visit_Assign(self, node):  # pylint: disable=invalid-name
        self.visit(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments[-1][target.id] = node.value

    def visit_AnnAssign(self, node):  # pylint: disable=invalid-name
        if node.value is not None:
            self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self.assignments[-1][node.target.id] = node.value

    def visit_ImportFrom(self, node):  # pylint: disable=invalid-name
        if node.module == "conftest":
            self.wait_function_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "wait_for_log_marker"
            )

    def visit_Call(self, node):  # pylint: disable=invalid-name
        direct_call = (
            isinstance(node.func, ast.Name)
            and node.func.id in self.wait_function_names
        )
        qualified_call = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "wait_for_log_marker"
        )
        log_argument = node.args[0] if node.args else next(
            (
                keyword.value
                for keyword in node.keywords
                if keyword.arg == "log_path"
            ),
            None,
        )
        if (
            (direct_call or qualified_call)
            and log_argument is not None
            and _resolves_to_manager_log_path(log_argument, self.assignments[-1])
        ):
            self.calls.append(node)
        self.generic_visit(node)


def _manager_log_readiness_calls(tree):
    visitor = _ManagerLogReadinessVisitor()
    visitor.visit(tree)
    return visitor.calls


def test_evidence_backed_integration_helpers_are_imported():
    offenders = []
    for filename, required_imports in REQUIRED_TOP_LEVEL_IMPORTS.items():
        path = INTEGRATION_TEST_DIR / filename
        imported = _top_level_imports(path)
        for imported_name, source_module in required_imports:
            if (imported_name, source_module) in imported:
                continue
            expected = (
                f"from {source_module} import {imported_name}"
                if source_module
                else f"import {imported_name}"
            )
            offenders.append(f"{path}: missing {expected}")

    assert offenders == []


def test_manager_log_readiness_uses_runtime_neutral_logs_command():
    offenders = []
    for filename in RUNTIME_LOG_READINESS_TESTS:
        path = INTEGRATION_TEST_DIR / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _has_common_runtime_log_readiness(tree):
            offenders.append(f"{path}: missing runtime log readiness")
        for node in _manager_log_readiness_calls(tree):
            offenders.append(f"{path}:{node.lineno}: manager log readiness")

    assert offenders == []


@pytest.mark.parametrize("filename,protocol", [("test_ts3server.py", "ts3"), ("test_qlserver.py", "a2s")])
def test_voice_and_quake_live_require_native_protocol_readiness(filename, protocol):
    tree = ast.parse((INTEGRATION_TEST_DIR / filename).read_text(encoding="utf-8"))
    readiness = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and _call_name(node) == "wait_for_info_protocol"]
    assert len(readiness) == 1
    assert isinstance(readiness[0].args[2], ast.Constant)
    assert readiness[0].args[2].value == protocol


def test_manager_log_guard_resolves_assigned_home_logs_path():
    tree = ast.parse(
        "def test_lifecycle():\n"
        '    log_path = home_dir / "logs" / "AlphaGSM-test.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [3]


def test_manager_log_guard_does_not_depend_on_home_variable_name():
    tree = ast.parse(
        "def test_lifecycle():\n"
        '    log_path = alphagsm_home / "logs" / f"AlphaGSM-{server_name}.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [3]


def test_manager_log_guard_resolves_module_session_tag_in_function_scope():
    tree = ast.parse(
        'SESSION_TAG = "AlphaGSM-IT#"\n'
        "def test_lifecycle():\n"
        '    log_path = alphagsm_home / "logs" / f"{SESSION_TAG}{server_name}.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [4]


def test_manager_log_guard_resolves_module_filename_constant():
    tree = ast.parse(
        'MANAGER_LOG = "AlphaGSM-static.log"\n'
        "def test_lifecycle():\n"
        '    log_path = alphagsm_home / "logs" / MANAGER_LOG\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [4]


def test_manager_log_guard_classifies_lowercase_logs_outside_install_dir():
    tree = ast.parse(
        "def test_lifecycle():\n"
        '    log_path = alphagsm_home / "logs" / "session.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [3]


def test_manager_log_guard_resolves_log_path_keyword_argument():
    tree = ast.parse(
        "def test_lifecycle():\n"
        "    wait_for_log_marker(\n"
        '        log_path=home_dir / "logs" / "AlphaGSM-test.log",\n'
        "        markers=['ready'],\n"
        "        timeout_seconds=30,\n"
        "    )\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [2]


def test_manager_log_guard_resolves_aliased_import():
    tree = ast.parse(
        "from conftest import wait_for_log_marker as wait_for_manager_log\n"
        "def test_lifecycle():\n"
        '    log_path = home_dir / "logs" / "AlphaGSM-test.log"\n'
        "    wait_for_manager_log(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [4]


def test_manager_log_guard_resolves_module_qualified_call():
    tree = ast.parse(
        "import conftest\n"
        "def test_lifecycle():\n"
        '    log_path = home_dir / "logs" / "AlphaGSM-test.log"\n'
        "    conftest.wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    calls = _manager_log_readiness_calls(tree)

    assert [call.lineno for call in calls] == [4]


def test_manager_log_guard_allows_game_owned_log_path():
    tree = ast.parse(
        "def test_lifecycle():\n"
        '    log_path = install_dir / "Game" / "Saved" / "Logs" / "Game.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    assert _manager_log_readiness_calls(tree) == []


def test_manager_log_guard_allows_lowercase_install_owned_log_path():
    tree = ast.parse(
        "def test_lifecycle():\n"
        '    log_path = install_dir / "logs" / "game.log"\n'
        "    wait_for_log_marker(log_path, ['ready'], 30)\n"
    )

    assert _manager_log_readiness_calls(tree) == []


def test_runtime_log_contract_covers_every_strict_source_log_user_and_sven():
    required = {"test_svenserver.py"}
    for filename in STRICT_SOURCE_A2S_TESTS:
        tree = ast.parse(
            (INTEGRATION_TEST_DIR / filename).read_text(encoding="utf-8")
        )
        if any(
            isinstance(node, ast.Call)
            and _call_name(node) == "wait_for_runtime_log_marker"
            for node in ast.walk(tree)
        ):
            required.add(filename)

    assert required <= set(RUNTIME_LOG_READINESS_TESTS)


def test_runtime_log_guard_rejects_readiness_only_in_unused_helper():
    tree = ast.parse(
        "def unused_helper():\n"
        "    wait_for_runtime_log_marker(env, server_name, ['ready'], 30)\n"
        + STRICT_SOURCE_FIXTURE
    )

    assert not _has_common_runtime_log_readiness(tree)


def test_integration_tests_do_not_use_manager_log_readiness_calls():
    offenders = []
    for path in _integration_test_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(
            f"{path}:{call.lineno}: manager log readiness"
            for call in _manager_log_readiness_calls(tree)
        )

    assert offenders == []


def test_wine_proton_tests_route_runtime_requirements_explicitly():
    offenders = []
    backend_selection = re.compile(
        r"selected_runtime_backend = effective_runtime_backend\(\s*"
        r"runtime_backend,\s*module_name=module_name,\s*\)"
    )
    runtime_branch = re.compile(
        r'if selected_runtime_backend == "process":\s*require_proton\(\)\s*'
        r'else:\s*require_command\("docker"\)\s*image = resolve_runtime_image\('
    )
    conditional_image = re.compile(
        r'if image is not None:\s*run_and_assert_ok\('
        r'env, server_name, "set", "image", image\)'
    )

    for filename in WINE_PROTON_RUNTIME_TESTS:
        path = INTEGRATION_TEST_DIR / filename
        text = path.read_text(encoding="utf-8")
        if not backend_selection.search(text):
            offenders.append(f"{path}: missing effective backend selection")
        if "image = None" not in text or not runtime_branch.search(text):
            offenders.append(f"{path}: missing explicit process/Docker requirements")
        if not conditional_image.search(text):
            offenders.append(f"{path}: image set is not Docker-only")
        if "require_command_for_runtime" in text:
            offenders.append(f"{path}: process-only helper used for Docker")

    assert offenders == []


def test_evidence_backed_integration_create_calls_use_canonical_module_ids():
    offenders = []
    for filename, canonical_id in CANONICAL_MODULE_IDS.items():
        path = INTEGRATION_TEST_DIR / filename
        create_module_id = _lifecycle_create_module_id(path)
        if create_module_id != canonical_id:
            offenders.append(
                f"{path}: create uses {create_module_id!r}, expected {canonical_id!r}"
            )

    assert offenders == []


def test_disabled_modules_have_matching_integration_test_files():
    offenders = []
    for module_name in _disabled_module_names():
        expected = INTEGRATION_TEST_DIR / ("test_" + module_name.replace(".", "_") + ".py")
        if not expected.is_file():
            offenders.append(f"{module_name}: missing {expected}")

    assert offenders == []


def test_integration_tests_do_not_allow_tcp_fallback_output():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if 'or "Server port is open" in query_result.stdout' in text:
            offenders.append(f"{path}: query fallback")
        if 'or "Server port is open" in info_result.stdout' in text:
            offenders.append(f"{path}: info fallback")

    assert offenders == []


def test_integration_tests_require_exact_protocol_assertions():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if '_info_data["protocol"] in (' in text:
            offenders.append(str(path))

    assert offenders == []


def test_integration_tests_do_not_soft_pass_query_info_commands():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "if query_result.returncode == 0:" in text:
            offenders.append(f"{path}: query")
        if "if info_result.returncode == 0:" in text:
            offenders.append(f"{path}: info")
        if "if info_json_result.returncode == 0:" in text:
            offenders.append(f"{path}: info-json")

    assert offenders == []


def test_a2s_integration_tests_do_not_accept_hibernation_as_success():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "wait_for_a2s_ready" in text and "Server is hibernating" in text:
            offenders.append(str(path))

    assert offenders == []


def test_source_integration_tests_require_strict_a2s_lifecycle():
    offenders = []
    for filename in STRICT_SOURCE_A2S_TESTS:
        path = INTEGRATION_TEST_DIR / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(_strict_source_a2s_violations(tree, path))

    assert offenders == []


def test_goldsrc_integration_tests_wait_for_a2s_before_query():
    offenders = []
    for filename in STRICT_GOLDSRC_A2S_TESTS:
        path = INTEGRATION_TEST_DIR / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        test_function = _test_function(tree)
        main_try = next(
            (
                statement
                for statement in (test_function.body if test_function else [])
                if isinstance(statement, ast.Try)
            ),
            None,
        )
        if main_try is None:
            offenders.append(f"{path}: missing lifecycle try/finally")
            continue

        calls = [
            (index, _direct_call(statement))
            for index, statement in enumerate(main_try.body)
        ]
        readiness_indexes = [
            index
            for index, call in calls
            if call is not None and _is_exact_a2s_readiness(call)
        ]
        query_indexes = [
            index
            for index, call in calls
            if call is not None and _alphagsm_command(call) == "query"
        ]
        if len(readiness_indexes) != 1:
            offenders.append(f"{path}: missing exact A2S readiness")
        elif not query_indexes or readiness_indexes[0] >= min(query_indexes):
            offenders.append(f"{path}: A2S readiness must precede query")

    assert offenders == []


def test_sven_goldsrc_integration_requires_strict_a2s_without_source_hibernation():
    path = INTEGRATION_TEST_DIR / "test_svenserver.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    assert _sven_goldsrc_violations(tree, path) == []


def test_strict_source_guard_rejects_console_comparison_split_from_a2s_wait():
    source = STRICT_SOURCE_FIXTURE.replace(
        "        info_data = wait_for_info_protocol(\n",
        '        if cached_info["protocol"] == "console":\n'
        "            wait_for_info_protocol(\n"
        '                env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
        "            )\n"
        "        info_data = wait_for_info_protocol(\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: console protocol fallback" in violations


def test_strict_source_guard_rejects_nonliteral_protocol_allowlist():
    source = STRICT_SOURCE_FIXTURE.replace(
        "        info_data = wait_for_info_protocol(\n",
        '        allowed_protocols = {"console", "a2s"}\n'
        '        if cached_info["protocol"] in allowed_protocols:\n'
        "            wait_for_info_protocol(\n"
        '                env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
        "            )\n"
        "        info_data = wait_for_info_protocol(\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: console protocol fallback" in violations


def test_strict_source_guard_rejects_runtime_conditional_readiness():
    source = STRICT_SOURCE_FIXTURE.replace(
        "        info_data = wait_for_info_protocol(\n"
        '            env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
        "        )\n",
        '        if runtime_backend == "docker":\n'
        "            info_data = wait_for_info_protocol(\n"
        '                env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
        "            )\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: missing unconditional exact A2S info readiness" in violations


def test_strict_source_guard_rejects_process_early_return_before_readiness():
    source = STRICT_SOURCE_FIXTURE.replace(
        "        run_and_assert_ok(env, server_name, \"status\")\n",
        "        run_and_assert_ok(env, server_name, \"status\")\n"
        '        if runtime_backend == "process":\n'
        "            return\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: early exit before A2S readiness" in violations


def test_strict_source_guard_rejects_direct_return_or_raise_before_readiness():
    for early_exit in ("        return\n", "        raise RuntimeError('stop')\n"):
        source = STRICT_SOURCE_FIXTURE.replace(
            "        run_and_assert_ok(env, server_name, \"status\")\n",
            "        run_and_assert_ok(env, server_name, \"status\")\n" + early_exit,
        )

        violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: early exit before A2S readiness" in violations


def test_strict_source_guard_rejects_nonliteral_hibernation_flag():
    source = STRICT_SOURCE_FIXTURE.replace(
        "set_source_hibernation(server_cfg_path, enabled=False)",
        "set_source_hibernation(server_cfg_path, enabled=disable_hibernation)",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: hibernation must use literal enabled=False" in violations


def test_strict_source_guard_rejects_extra_hibernation_call():
    source = STRICT_SOURCE_FIXTURE.replace(
        "    run_and_assert_ok(env, server_name, \"start\")\n",
        "    set_source_hibernation(server_cfg_path, enabled=False)\n"
        "    run_and_assert_ok(env, server_name, \"start\")\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: expected exactly one hibernation call" in violations


def test_strict_source_guard_rejects_hibernation_after_start():
    source = STRICT_SOURCE_FIXTURE.replace(
        "    set_source_hibernation(server_cfg_path, enabled=False)\n"
        "    run_and_assert_ok(env, server_name, \"start\")\n",
        "    run_and_assert_ok(env, server_name, \"start\")\n"
        "    set_source_hibernation(server_cfg_path, enabled=False)\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: hibernation must precede start on the common path" in violations


def test_strict_source_guard_ties_assertions_to_final_info_json_payload():
    source = STRICT_SOURCE_FIXTURE.replace(
        'assert final_info["protocol"] == "a2s"',
        'assert unrelated_info["protocol"] == "a2s"',
    ).replace(
        'assert final_info["port"] == port',
        'assert unrelated_info["port"] == port',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info JSON lacks exact A2S protocol assertion" in violations
    assert "fixture.py: final info JSON lacks exact port assertion" in violations


def test_strict_source_guard_rejects_final_payload_reassignment():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        assert final_info["protocol"] == "a2s"\n',
        "        final_info = unrelated_info\n"
        '        assert final_info["protocol"] == "a2s"\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info JSON payload mutated before assertions" in violations


def test_strict_source_guard_rejects_conditional_final_payload_reassignment():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        assert final_info["protocol"] == "a2s"\n',
        '        if runtime_backend == "docker":\n'
        "            final_info = unrelated_info\n"
        '        assert final_info["protocol"] == "a2s"\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info JSON payload mutated before assertions" in violations


def test_strict_source_guard_uses_the_last_info_json_payload():
    earlier_payload = (
        "        earlier_result = run_and_assert_ok(\n"
        '            env, server_name, "info", "--json"\n'
        "        )\n"
        "        earlier_info = json.loads(earlier_result.stdout.strip())\n"
        '        assert earlier_info["protocol"] == "a2s"\n'
        '        assert earlier_info["port"] == port\n'
    )
    source = STRICT_SOURCE_FIXTURE.replace(
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
        earlier_payload
        + '        query_result = run_and_assert_ok(env, server_name, "query")\n',
    ).replace(
        '        assert final_info["protocol"] == "a2s"\n',
        "",
    ).replace(
        '        assert final_info["port"] == port\n',
        "",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info JSON lacks exact A2S protocol assertion" in violations
    assert "fixture.py: final info JSON lacks exact port assertion" in violations


def test_strict_source_guard_requires_each_lifecycle_stage_independently():
    stages = {
        '    run_and_assert_ok(env, server_name, "create", module_name)\n': "create",
        '    setup_result = run_and_assert_ok(env, server_name, "setup")\n': "setup",
        '    run_and_assert_ok(env, server_name, "start")\n': "start",
        '        run_and_assert_ok(env, server_name, "status")\n': "status",
        '        query_result = run_and_assert_ok(env, server_name, "query")\n': "query",
        '        info_result = run_and_assert_ok(env, server_name, "info")\n': "human-readable info",
        "        info_json_result = run_and_assert_ok(\n"
        '            env, server_name, "info", "--json"\n'
        "        )\n": "info --json",
        '        stop_result = run_alphagsm(env, server_name, "stop")\n': "stop in finally",
        "    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)\n": "UDP shutdown verification",
    }
    for statement, stage in stages.items():
        source = STRICT_SOURCE_FIXTURE.replace(statement, "")

        violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: missing {stage}" in violations


def test_strict_source_guard_requires_create_setup_start_order_before_try():
    swapped = STRICT_SOURCE_FIXTURE.replace(
        '    run_and_assert_ok(env, server_name, "create", module_name)\n'
        '    setup_result = run_and_assert_ok(env, server_name, "setup")\n',
        '    setup_result = run_and_assert_ok(env, server_name, "setup")\n'
        '    run_and_assert_ok(env, server_name, "create", module_name)\n',
    )
    start_in_try = STRICT_SOURCE_FIXTURE.replace(
        '    run_and_assert_ok(env, server_name, "start")\n'
        "    try:\n",
        "    try:\n"
        '        run_and_assert_ok(env, server_name, "start")\n',
    )
    for source in (swapped, start_in_try):
        violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: create/setup/start must precede lifecycle try in order" in violations


def test_strict_source_guard_rejects_unchecked_lifecycle_runners():
    mutations = {
        'run_and_assert_ok(env, server_name, "create", module_name)': (
            'run_alphagsm(env, server_name, "create", module_name)',
            "create",
        ),
        'run_and_assert_ok(env, server_name, "start")': (
            'run_alphagsm(env, server_name, "start")',
            "start",
        ),
        'run_and_assert_ok(env, server_name, "status")': (
            'run_alphagsm(env, server_name, "status")',
            "status",
        ),
        'run_and_assert_ok(env, server_name, "query")': (
            'run_alphagsm(env, server_name, "query")',
            "query",
        ),
        'run_and_assert_ok(env, server_name, "info")': (
            'run_alphagsm(env, server_name, "info")',
            "human-readable info",
        ),
        'run_and_assert_ok(\n            env, server_name, "info", "--json"\n        )': (
            'run_alphagsm(\n            env, server_name, "info", "--json"\n        )',
            "info --json",
        ),
    }
    for asserted, (raw, label) in mutations.items():
        source = STRICT_SOURCE_FIXTURE.replace(asserted, raw)

        violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: {label} must use run_and_assert_ok" in violations


def test_strict_source_guard_rejects_extra_unchecked_lifecycle_runner():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
        '        run_alphagsm(env, server_name, "query")\n'
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: query must use run_and_assert_ok" in violations


def test_strict_source_guard_requires_raw_setup_result_assertion():
    source = STRICT_SOURCE_FIXTURE.replace(
        'setup_result = run_and_assert_ok(env, server_name, "setup")',
        'setup_result = run_alphagsm(env, server_name, "setup")',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: raw setup result must be asserted successful" in violations


def test_strict_source_guard_allows_explicitly_asserted_raw_setup():
    source = STRICT_SOURCE_FIXTURE.replace(
        '    setup_result = run_and_assert_ok(env, server_name, "setup")\n',
        '    setup_result = run_alphagsm(env, server_name, "setup")\n'
        "    assert setup_result.returncode == 0\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: raw setup result must be asserted successful" not in violations


def test_strict_source_guard_requires_readiness_before_each_info_stage():
    readiness = (
        "        info_data = wait_for_info_protocol(\n"
        '            env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
        "        )\n"
    )
    source = STRICT_SOURCE_FIXTURE.replace(readiness, "").replace(
        '        info_json_result = run_and_assert_ok(\n',
        readiness + '        info_json_result = run_and_assert_ok(\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: A2S readiness follows query/info lifecycle checks" in violations


def test_strict_source_guard_rejects_query_info_order_swap():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        query_result = run_and_assert_ok(env, server_name, "query")\n'
        '        info_result = run_and_assert_ok(env, server_name, "info")\n',
        '        info_result = run_and_assert_ok(env, server_name, "info")\n'
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: lifecycle stages are out of order" in violations


def test_strict_source_guard_rejects_status_after_query():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        run_and_assert_ok(env, server_name, "status")\n',
        "",
    ).replace(
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
        '        query_result = run_and_assert_ok(env, server_name, "query")\n'
        '        run_and_assert_ok(env, server_name, "status")\n',
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: lifecycle stages are out of order" in violations


def test_strict_source_guard_requires_captured_asserted_stop_result():
    source = STRICT_SOURCE_FIXTURE.replace(
        '        stop_result = run_alphagsm(env, server_name, "stop")\n'
        '        log_command_result("alphagsm stop", stop_result)\n',
        "        log_command_result(\n"
        '            "alphagsm stop", run_alphagsm(env, server_name, "stop")\n'
        "        )\n",
    ).replace(
        "    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout\n",
        "",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: stop must be captured in finally" in violations
    assert "fixture.py: stop result must be asserted successful after finally" in violations


def test_strict_source_guard_rejects_shutdown_before_stop_assertion():
    source = STRICT_SOURCE_FIXTURE.replace(
        "    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout\n"
        "    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)\n",
        "    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)\n"
        "    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout\n",
    )

    violations = _strict_source_a2s_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: UDP shutdown verification must follow stop assertion" in violations


def test_sven_goldsrc_guard_rejects_source_hibernation_and_weak_a2s_flow():
    tree = ast.parse(
        "from conftest import find_source_server_cfg, set_source_hibernation\n"
        + STRICT_SOURCE_FIXTURE.replace(
            "        info_data = wait_for_info_protocol(\n"
            '            env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
            "        )\n",
            '        if runtime_backend == "docker":\n'
            "            info_data = wait_for_info_protocol(\n"
            '                env, server_name, "a2s", START_TIMEOUT, expected_port=port\n'
            "            )\n",
        ).replace(
            'assert final_info["protocol"] == "a2s"',
            'assert unrelated_info["protocol"] == "a2s"',
        ).replace(
            'assert final_info["port"] == port',
            'assert unrelated_info["port"] == port',
        )
    )

    violations = _sven_goldsrc_violations(tree, "test_svenserver.py")

    assert "test_svenserver.py: Source hibernation API is forbidden" in violations
    assert "test_svenserver.py: missing unconditional exact A2S info readiness" in violations
    assert "test_svenserver.py: missing direct raw A2S validation" in violations
    assert "test_svenserver.py: final info JSON lacks exact A2S protocol assertion" in violations
    assert "test_svenserver.py: final info JSON lacks exact port assertion" in violations


def test_sven_goldsrc_guard_rejects_any_local_hibernation_helper_call():
    source = STRICT_SOURCE_FIXTURE.replace(
        "set_source_hibernation(server_cfg_path, enabled=False)",
        "_set_goldsrc_hibernation(server_cfg_path, enabled=False)",
    ).replace(
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
        "        wait_for_a2s_ready(query_host, port, START_TIMEOUT)\n"
        '        query_result = run_and_assert_ok(env, server_name, "query")\n',
    )

    violations = _sven_goldsrc_violations(
        ast.parse(source), "test_svenserver.py"
    )

    assert "test_svenserver.py: Source hibernation API is forbidden" in violations


def test_runtime_aware_integration_tests_use_alphagsm_info_surface_only():
    offenders = []
    for filename, protocol in RUNTIME_AWARE_PROTOCOL_TESTS.items():
        path = INTEGRATION_TEST_DIR / filename
        text = path.read_text(encoding="utf-8")
        if f'"{protocol}"' not in text or "wait_for_info_protocol" not in text:
            offenders.append(f"{path}: missing {protocol} info readiness")
        if "wait_for_a2s_ready(" in text:
            offenders.append(f"{path}: raw A2S readiness")
        if "detect_query_host" in text:
            offenders.append(f"{path}: guessed query host")

    assert offenders == []


NS2_LIFECYCLE_FIXTURE = '''
import json

from conftest import (
    capture_alphagsm_stop,
    pick_free_tcp_port_group,
    run_and_assert_ok,
    wait_for_info_protocol,
    wait_for_udp_closed,
)

def test_ns2_lifecycle(tmp_path):
    selected_port = pick_free_tcp_port_group(2)
    a2s_endpoint = selected_port + 1
    run_and_assert_ok(env, instance_name, "create", module_name, allow_known_steamcmd_skip=False)
    run_and_assert_ok(env, instance_name, "setup", "-n", str(selected_port), install_dir, allow_known_steamcmd_skip=False)
    run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)
    try:
        ready_info = wait_for_info_protocol(
            env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint
        )
        run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)
        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)
        assert "Server is responding" in query_result.stdout
        info_result = run_and_assert_ok(env, instance_name, "info", allow_known_steamcmd_skip=False)
        assert "Protocol" in info_result.stdout
        json_result = run_and_assert_ok(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)
        final_payload = json.loads(json_result.stdout.strip())
        assert final_payload["protocol"] == "a2s"
        assert final_payload["port"] == a2s_endpoint
    finally:
        cleanup_result = capture_alphagsm_stop(
            env, instance_name, sys.exc_info()[1]
        )
    assert cleanup_result.returncode == 0, cleanup_result.stderr or cleanup_result.stdout
    wait_for_udp_closed("127.0.0.1", a2s_endpoint, STOP_TIMEOUT)
'''


def _ns2_lifecycle_violations(tree, path):
    violations = []
    lifecycle = _test_function(tree)
    if lifecycle is None:
        return [f"{path}: missing lifecycle test"]

    lifecycle_helpers = {
        "capture_alphagsm_stop",
        "pick_free_tcp_port_group",
        "run_and_assert_ok",
        "wait_for_info_protocol",
        "wait_for_udp_closed",
    }
    exact_import_counts = {helper: 0 for helper in lifecycle_helpers}
    rebound_helpers = set()
    exact_json_imports = 0
    json_rebound = False
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                bound_name = alias.asname or alias.name
                if bound_name == "json":
                    json_rebound = True
                if bound_name not in lifecycle_helpers:
                    continue
                if (
                    statement.module == "conftest"
                    and alias.asname is None
                    and alias.name == bound_name
                ):
                    exact_import_counts[bound_name] += 1
                else:
                    rebound_helpers.add(bound_name)
            continue
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                if bound_name == "json":
                    if alias.name == "json" and alias.asname is None:
                        exact_json_imports += 1
                    else:
                        json_rebound = True
                if bound_name in lifecycle_helpers:
                    rebound_helpers.add(bound_name)
            continue
        rebound_helpers.update(
            helper
            for helper in lifecycle_helpers
            if _statement_mutates_name(statement, helper)
        )
        if _statement_mutates_name(statement, "json"):
            json_rebound = True
    if any(count != 1 for count in exact_import_counts.values()):
        violations.append(
            f"{path}: lifecycle helpers require exact conftest imports"
        )
    violations.extend(
        f"{path}: lifecycle helper rebound: {helper}"
        for helper in sorted(rebound_helpers)
    )
    if exact_json_imports != 1 or json_rebound:
        violations.append(
            f"{path}: json requires an exact import and no rebinding"
        )

    indirect_helper_call = any(
        _call_name(node) in lifecycle_helpers
        and not (
            isinstance(node.func, ast.Name)
            and node.func.id == _call_name(node)
        )
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
    )
    if indirect_helper_call:
        violations.append(f"{path}: lifecycle helpers must be direct name calls")

    run_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call) and _call_name(node) == "run_and_assert_ok"
    ]

    def disables_known_steamcmd_skip(call):
        skip_values = [
            keyword.value
            for keyword in call.keywords
            if keyword.arg == "allow_known_steamcmd_skip"
        ]
        return (
            len(skip_values) == 1
            and _constant_value(skip_values[0]) is False
        )

    if any(not disables_known_steamcmd_skip(call) for call in run_calls):
        violations.append(
            f"{path}: run_and_assert_ok must disable known SteamCMD skips"
        )

    lifecycle_escapes = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"skip", "xfail"}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pytest"
        for node in ast.walk(lifecycle)
    )
    if lifecycle_escapes:
        violations.append(f"{path}: lifecycle must not skip or xfail")

    try_indexes = [
        index
        for index, statement in enumerate(lifecycle.body)
        if isinstance(statement, ast.Try)
    ]
    if len(try_indexes) != 1:
        return [f"{path}: lifecycle must have one unconditional try statement"]
    try_index = try_indexes[0]
    main_try = lifecycle.body[try_index]

    selected_port_name = None
    selected_port_index = None
    for index, statement in enumerate(lifecycle.body[:try_index]):
        name, call = _direct_assigned_call(statement)
        if _call_name(call) != "pick_free_tcp_port_group":
            continue
        if _constant_value(_call_argument(call, 0, "count")) == 2:
            selected_port_name = name
            selected_port_index = index
            break
    if selected_port_name is None:
        violations.append(f"{path}: missing unconditional consecutive port reservation")

    a2s_port_name = None
    a2s_port_index = None
    if selected_port_name is not None:
        for index, statement in enumerate(lifecycle.body[:try_index]):
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            expression = statement.value
            if not isinstance(expression, ast.BinOp) or not isinstance(expression.op, ast.Add):
                continue
            operands = (expression.left, expression.right)
            has_selected_port = any(
                isinstance(operand, ast.Name) and operand.id == selected_port_name
                for operand in operands
            )
            has_one = any(_constant_value(operand) == 1 for operand in operands)
            if has_selected_port and has_one:
                a2s_port_name = targets[0].id
                a2s_port_index = index
                break
    if a2s_port_name is None:
        violations.append(f"{path}: missing unconditional A2S port offset")

    endpoint_mutated = False
    if selected_port_name is not None and selected_port_index is not None:
        endpoint_mutated = any(
            _statement_mutates_name(statement, selected_port_name)
            for statement in lifecycle.body[selected_port_index + 1 :]
        )
    if a2s_port_name is not None and a2s_port_index is not None:
        endpoint_mutated = endpoint_mutated or any(
            _statement_mutates_name(statement, a2s_port_name)
            for statement in lifecycle.body[a2s_port_index + 1 :]
        )
    if endpoint_mutated:
        violations.append(f"{path}: selected/A2S port mutated after definition")

    def call_stage(call):
        if _call_name(call) == "wait_for_info_protocol":
            return "readiness"
        command = _alphagsm_command(call)
        if command == "info" and _call_has_argument(call, "--json"):
            return "info --json"
        if command in {"create", "setup", "start", "status", "query", "info"}:
            return command
        return None

    pre_try_stages = ("create", "setup", "start")
    lifecycle_stages = ("readiness", "status", "query", "info", "info --json")
    all_stages = pre_try_stages + lifecycle_stages
    occurrences = {stage: [] for stage in all_stages}

    def collect_calls(statements, region):
        for index, statement in enumerate(statements):
            direct_call = _direct_call(statement)
            for call in (
                node for node in ast.walk(statement) if isinstance(node, ast.Call)
            ):
                stage = call_stage(call)
                if stage in occurrences:
                    occurrences[stage].append(
                        (region, index, call, call is direct_call)
                    )

    collect_calls(lifecycle.body[:try_index], "pre")
    collect_calls(main_try.body, "try")
    for handler in main_try.handlers:
        collect_calls(handler.body, "handler")
    collect_calls(main_try.orelse, "else")
    collect_calls(main_try.finalbody, "finally")
    collect_calls(lifecycle.body[try_index + 1 :], "post")

    stage_entries = {}
    for stage in all_stages:
        stage_occurrences = occurrences[stage]
        if len(stage_occurrences) != 1:
            if not stage_occurrences:
                violations.append(f"{path}: missing unconditional {stage}")
            else:
                violations.append(
                    f"{path}: {stage} lifecycle call must appear exactly once"
                )
            continue
        region, index, call, is_direct = stage_occurrences[0]
        expected_region = "pre" if stage in pre_try_stages else "try"
        if region != expected_region or not is_direct:
            violations.append(f"{path}: missing unconditional {stage}")
            continue
        stage_entries[stage] = (index, call)

    for stage in pre_try_stages + ("query", "status", "info", "info --json"):
        if any(
            _call_name(call) != "run_and_assert_ok"
            for _region, _index, call, _is_direct in occurrences[stage]
        ):
            violations.append(f"{path}: {stage} must use run_and_assert_ok")

    pre_try_entries = {
        stage: stage_entries[stage]
        for stage in pre_try_stages
        if stage in stage_entries
    }
    if all(stage in pre_try_entries for stage in pre_try_stages):
        pre_try_indexes = [pre_try_entries[stage][0] for stage in pre_try_stages]
        if pre_try_indexes != sorted(pre_try_indexes):
            violations.append(f"{path}: create/setup/start are out of order")

    if all(stage in stage_entries for stage in lifecycle_stages):
        stage_indexes = [stage_entries[stage][0] for stage in lifecycle_stages]
        if stage_indexes != sorted(stage_indexes):
            violations.append(
                f"{path}: readiness/status/query/info/info-json are out of order"
            )

    readiness_entry = stage_entries.get("readiness")
    if readiness_entry is not None:
        readiness = readiness_entry[1]
        expected_port = _call_argument(readiness, 4, "expected_port")
        if not (
            _constant_value(_call_argument(readiness, 2, "expected_protocol")) == "a2s"
            and a2s_port_name is not None
            and isinstance(expected_port, ast.Name)
            and expected_port.id == a2s_port_name
        ):
            violations.append(f"{path}: readiness must target the exact A2S port")

    setup_entry = stage_entries.get("setup")
    if setup_entry is not None:
        setup_call = setup_entry[1]
        setup_port = setup_call.args[4] if len(setup_call.args) > 4 else None
        setup_uses_selected_port = (
            len(setup_call.args) > 4
            and _constant_value(setup_call.args[3]) == "-n"
            and isinstance(setup_port, ast.Call)
            and isinstance(setup_port.func, ast.Name)
            and setup_port.func.id == "str"
            and len(setup_port.args) == 1
            and not setup_port.keywords
            and selected_port_name is not None
            and isinstance(setup_port.args[0], ast.Name)
            and setup_port.args[0].id == selected_port_name
        )
        if not setup_uses_selected_port:
            violations.append(
                f"{path}: setup must pass str(selected port) after -n"
            )

    def exact_stdout_membership(statement, result_name, expected_text):
        if (
            result_name is None
            or not isinstance(statement, ast.Assert)
            or statement.msg is not None
            or not isinstance(statement.test, ast.Compare)
        ):
            return False
        comparison = statement.test
        stdout = comparison.comparators[0] if comparison.comparators else None
        return (
            len(comparison.ops) == 1
            and isinstance(comparison.ops[0], ast.In)
            and len(comparison.comparators) == 1
            and _constant_value(comparison.left) == expected_text
            and isinstance(stdout, ast.Attribute)
            and stdout.attr == "stdout"
            and isinstance(stdout.value, ast.Name)
            and stdout.value.id == result_name
        )

    query_entry = stage_entries.get("query")
    info_entry = stage_entries.get("info")
    info_json_entry = stage_entries.get("info --json")
    query_result_name = None
    query_assertion_index = None
    if query_entry is not None and info_entry is not None:
        query_index = query_entry[0]
        query_result_name, _query_call = _direct_assigned_call(
            main_try.body[query_index]
        )
        query_assertion_index = next(
            (
                index
                for index in range(query_index + 1, info_entry[0])
                if exact_stdout_membership(
                    main_try.body[index],
                    query_result_name,
                    "Server is responding",
                )
            ),
            None,
        )
        if query_assertion_index is not None and any(
            _statement_mutates_name(statement, query_result_name)
            for statement in main_try.body[
                query_index + 1 : query_assertion_index
            ]
        ):
            violations.append(
                f"{path}: query result mutated before response assertion"
            )
    if query_assertion_index is None:
        violations.append(f"{path}: query response assertion is required")

    info_assertion_index = None
    if info_entry is not None and info_json_entry is not None:
        info_index = info_entry[0]
        info_result_name, _info_call = _direct_assigned_call(main_try.body[info_index])
        info_assertion_index = next(
            (
                index
                for index in range(info_index + 1, info_json_entry[0])
                if exact_stdout_membership(
                    main_try.body[index],
                    info_result_name,
                    "Protocol",
                )
            ),
            None,
        )
        if info_assertion_index is not None and any(
            _statement_mutates_name(statement, info_result_name)
            for statement in main_try.body[info_index + 1 : info_assertion_index]
        ):
            violations.append(
                f"{path}: info result mutated before output assertion"
            )
    if info_assertion_index is None:
        violations.append(
            f"{path}: info output assertion must be an exact plain comparison"
        )

    result_index, payload_index, payload_name = _final_info_payload(main_try.body)
    info_json_result_name = None
    if result_index is not None:
        info_json_result_name, _info_json_call = _direct_assigned_call(
            main_try.body[result_index]
        )
    payload_call = None
    if payload_index is not None:
        _payload_target, payload_call = _direct_assigned_call(
            main_try.body[payload_index]
        )
    parse_argument = payload_call.args[0] if payload_call and payload_call.args else None
    exact_json_loads = (
        payload_call is not None
        and isinstance(payload_call.func, ast.Attribute)
        and payload_call.func.attr == "loads"
        and isinstance(payload_call.func.value, ast.Name)
        and payload_call.func.value.id == "json"
        and len(payload_call.args) == 1
        and not payload_call.keywords
        and isinstance(parse_argument, ast.Call)
        and not parse_argument.args
        and not parse_argument.keywords
        and isinstance(parse_argument.func, ast.Attribute)
        and parse_argument.func.attr == "strip"
        and isinstance(parse_argument.func.value, ast.Attribute)
        and parse_argument.func.value.attr == "stdout"
        and isinstance(parse_argument.func.value.value, ast.Name)
        and parse_argument.func.value.value.id == info_json_result_name
    )
    if not exact_json_loads:
        violations.append(f"{path}: final info payload must use exact json.loads")
    if (
        result_index is not None
        and payload_index is not None
        and info_json_result_name is not None
        and any(
            _statement_mutates_name(statement, info_json_result_name)
            for statement in main_try.body[result_index + 1 : payload_index]
        )
    ):
        violations.append(f"{path}: info JSON result mutated before parsing")
    if payload_name is None:
        violations.append(f"{path}: missing final info JSON payload")
    else:
        assertion_statements = main_try.body[payload_index + 1 :]

        def exact_payload_assertion(statement, key, expected, *, expected_is_name=False):
            if not isinstance(statement, ast.Assert) or not isinstance(
                statement.test, ast.Compare
            ):
                return False
            comparison = statement.test
            if (
                len(comparison.ops) != 1
                or not isinstance(comparison.ops[0], ast.Eq)
                or len(comparison.comparators) != 1
            ):
                return False
            operands = (comparison.left, comparison.comparators[0])
            has_payload_value = any(
                _subscript_matches(operand, payload_name, key) for operand in operands
            )
            if expected_is_name:
                has_expected = any(
                    isinstance(operand, ast.Name) and operand.id == expected
                    for operand in operands
                )
            else:
                has_expected = any(
                    _constant_value(operand) == expected for operand in operands
                )
            return has_payload_value and has_expected

        protocol_assertions = [
            index
            for index, statement in enumerate(assertion_statements)
            if exact_payload_assertion(statement, "protocol", "a2s")
        ]
        port_assertions = [
            index
            for index, statement in enumerate(assertion_statements)
            if a2s_port_name is not None
            and exact_payload_assertion(
                statement,
                "port",
                a2s_port_name,
                expected_is_name=True,
            )
        ]
        if not protocol_assertions or not port_assertions:
            violations.append(
                f"{path}: final info JSON assertions must be plain exact comparisons"
            )
        if not protocol_assertions:
            violations.append(f"{path}: final info JSON lacks exact A2S assertion")
        if not port_assertions:
            violations.append(f"{path}: final info JSON lacks exact port assertion")
        last_assertion = max(
            protocol_assertions + port_assertions,
            default=-1,
        )
        if any(
            _statement_mutates_name(statement, payload_name)
            for statement in assertion_statements[: last_assertion + 1]
        ):
            violations.append(
                f"{path}: final info JSON payload mutated before assertions"
            )
        payload_following_statements = [
            *main_try.body[payload_index + 1 :],
            *main_try.orelse,
            *main_try.finalbody,
            *lifecycle.body[try_index + 1 :],
        ]
        for handler in main_try.handlers:
            payload_following_statements.extend(handler.body)
        if any(
            _statement_mutates_name(statement, payload_name)
            for statement in payload_following_statements
        ):
            violations.append(
                f"{path}: final info JSON payload mutated after parsing"
            )

    if main_try.handlers:
        violations.append(f"{path}: lifecycle try must not catch exceptions")

    raw_stop_or_logging = any(
        _alphagsm_command(call) == "stop" or _call_name(call) == "log_command_result"
        for statement in main_try.finalbody
        for call in ast.walk(statement)
        if isinstance(call, ast.Call)
    )
    if raw_stop_or_logging:
        violations.append(f"{path}: raw stop/logging in finally is forbidden")

    readiness_call = readiness_entry[1] if readiness_entry is not None else None
    expected_env = (
        _call_argument(readiness_call, 0, "env")
        if readiness_call is not None
        else None
    )
    expected_server = (
        _call_argument(readiness_call, 1, "server_name")
        if readiness_call is not None
        else None
    )

    def same_name(left, right):
        return (
            isinstance(left, ast.Name)
            and isinstance(right, ast.Name)
            and left.id == right.id
        )

    def is_lifecycle_exception(node):
        if not isinstance(node, ast.Subscript) or _constant_value(node.slice) != 1:
            return False
        exc_info_call = node.value
        return (
            isinstance(exc_info_call, ast.Call)
            and not exc_info_call.args
            and not exc_info_call.keywords
            and isinstance(exc_info_call.func, ast.Attribute)
            and exc_info_call.func.attr == "exc_info"
            and isinstance(exc_info_call.func.value, ast.Name)
            and exc_info_call.func.value.id == "sys"
        )

    finalbody = main_try.finalbody
    finally_contains_masking_statement = any(
        isinstance(node, (ast.Assert, ast.Raise))
        for statement in finalbody
        for node in ast.walk(statement)
    )
    bound_exception_name = None
    capture_statement_index = 0
    if len(finalbody) == 2:
        binding = finalbody[0]
        if (
            isinstance(binding, ast.Assign)
            and len(binding.targets) == 1
            and isinstance(binding.targets[0], ast.Name)
            and is_lifecycle_exception(binding.value)
        ):
            bound_exception_name = binding.targets[0].id
            capture_statement_index = 1
        elif (
            isinstance(binding, ast.AnnAssign)
            and isinstance(binding.target, ast.Name)
            and is_lifecycle_exception(binding.value)
        ):
            bound_exception_name = binding.target.id
            capture_statement_index = 1

    stop_result_name = None
    capture_call = None
    if len(finalbody) in {1, 2} and capture_statement_index < len(finalbody):
        candidate_name, candidate_call = _direct_assigned_call(
            finalbody[capture_statement_index]
        )
        if _call_name(candidate_call) == "capture_alphagsm_stop":
            stop_result_name = candidate_name
            capture_call = candidate_call

    allowed_finally_shape = (
        not finally_contains_masking_statement
        and capture_call is not None
        and (
            len(finalbody) == 1
            or (len(finalbody) == 2 and bound_exception_name is not None)
        )
    )
    if not allowed_finally_shape:
        violations.append(f"{path}: finally must only capture AlphaGSM stop")

    capture_exception = (
        capture_call.args[2]
        if capture_call is not None and len(capture_call.args) == 3
        else None
    )
    uses_bound_exception = (
        bound_exception_name is not None
        and isinstance(capture_exception, ast.Name)
        and capture_exception.id == bound_exception_name
    )
    exact_capture = (
        capture_call is not None
        and len(capture_call.args) == 3
        and not capture_call.keywords
        and same_name(capture_call.args[0], expected_env)
        and same_name(capture_call.args[1], expected_server)
        and (is_lifecycle_exception(capture_exception) or uses_bound_exception)
    )
    if not exact_capture:
        stop_result_name = None
        violations.append(
            f"{path}: finally must assign exact failure-preserving stop capture"
        )

    def exact_stop_assertion(statement, result_name):
        if (
            result_name is None
            or not isinstance(statement, ast.Assert)
            or not isinstance(statement.test, ast.Compare)
            or statement.msg is None
            or any(isinstance(node, ast.NamedExpr) for node in ast.walk(statement))
        ):
            return False
        comparison = statement.test
        if (
            len(comparison.ops) != 1
            or not isinstance(comparison.ops[0], ast.Eq)
            or len(comparison.comparators) != 1
            or _constant_value(comparison.comparators[0]) != 0
            or not isinstance(comparison.left, ast.Attribute)
            or comparison.left.attr != "returncode"
            or not isinstance(comparison.left.value, ast.Name)
            or comparison.left.value.id != result_name
        ):
            return False
        context_attributes = {
            node.attr
            for node in ast.walk(statement.msg)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == result_name
        }
        return {"stderr", "stdout"}.issubset(context_attributes)

    post_try = lifecycle.body[try_index + 1 :]
    has_early_exit = any(
        isinstance(node, (ast.Return, ast.Break, ast.Continue))
        for node in ast.walk(lifecycle)
    )
    stop_assertion = post_try[0] if post_try else None
    shutdown_call = _direct_call(post_try[1]) if len(post_try) > 1 else None
    exact_direct_stop_assertion = exact_stop_assertion(
        stop_assertion,
        stop_result_name,
    )
    if not exact_direct_stop_assertion:
        violations.append(
            f"{path}: stop assertion must be an exact direct comparison"
        )
    post_contract_valid = (
        not has_early_exit
        and len(post_try) == 2
        and stop_result_name is not None
        and exact_direct_stop_assertion
        and _call_name(shutdown_call) == "wait_for_udp_closed"
    )
    if not post_contract_valid:
        violations.append(
            f"{path}: stop assertion and closure must be direct and reachable"
        )

    stop_assert_indexes = [
        index
        for index, statement in enumerate(post_try)
        if stop_result_name is not None
        and exact_stop_assertion(statement, stop_result_name)
    ]
    shutdown_indexes = [
        index
        for index, statement in enumerate(post_try)
        if _call_name(_direct_call(statement)) == "wait_for_udp_closed"
    ]
    if not stop_assert_indexes:
        violations.append(f"{path}: stop result must be asserted after try")
    if not shutdown_indexes:
        violations.append(f"{path}: missing unconditional UDP shutdown verification")
    if (
        stop_assert_indexes
        and shutdown_indexes
        and shutdown_indexes[0] < stop_assert_indexes[0]
    ):
        violations.append(
            f"{path}: UDP shutdown verification must follow stop assertion"
        )

    if shutdown_call is not None:
        shutdown_host = _call_argument(shutdown_call, 0, "host")
        shutdown_port = _call_argument(shutdown_call, 1, "port")
        if not (
            _constant_value(shutdown_host) == "127.0.0.1"
            and a2s_port_name is not None
            and isinstance(shutdown_port, ast.Name)
            and shutdown_port.id == a2s_port_name
        ):
            violations.append(
                f"{path}: UDP shutdown must target localhost and the A2S port"
            )

    return violations


def test_ns2_integrations_use_adjacent_a2s_port_and_preserve_lifecycle_failures():
    offenders = []
    for filename in ("test_ns2server.py", "test_ns2cserver.py"):
        path = INTEGRATION_TEST_DIR / filename
        offenders.extend(
            _ns2_lifecycle_violations(
                ast.parse(path.read_text(encoding="utf-8")),
                filename,
            )
        )

    assert offenders == []


def test_ns2_guard_accepts_strict_direct_lifecycle_fixture():
    assert _ns2_lifecycle_violations(
        ast.parse(NS2_LIFECYCLE_FIXTURE), "fixture.py"
    ) == []


def test_ns2_guard_requires_exact_conftest_lifecycle_helper_imports():
    mutations = (
        (
            "    run_and_assert_ok,\n",
            "    run_and_assert_ok as lifecycle_runner,\n",
        ),
        (
            "    wait_for_info_protocol,\n",
            "",
        ),
        (
            "    pick_free_tcp_port_group,\n",
            "",
        ),
        (
            "from conftest import (\n",
            "from lifecycle_helpers import (\n",
        ),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: lifecycle helpers require exact conftest imports" in violations


def test_ns2_guard_rejects_lifecycle_helper_rebinding_in_any_scope():
    function_anchor = "def test_ns2_lifecycle(tmp_path):\n"
    mutations = (
        (
            function_anchor,
            "run_and_assert_ok = replacement_runner\n\n" + function_anchor,
            "run_and_assert_ok",
        ),
        (
            function_anchor,
            "def wait_for_info_protocol(*args):\n    pass\n\n" + function_anchor,
            "wait_for_info_protocol",
        ),
        (
            function_anchor,
            "def test_ns2_lifecycle(tmp_path, capture_alphagsm_stop):\n",
            "capture_alphagsm_stop",
        ),
        (
            "    selected_port = pick_free_tcp_port_group(2)\n",
            "    [None for wait_for_udp_closed in lifecycle_helpers]\n"
            "    selected_port = pick_free_tcp_port_group(2)\n",
            "wait_for_udp_closed",
        ),
        (
            function_anchor,
            "pick_free_tcp_port_group = replacement_port_picker\n\n"
            + function_anchor,
            "pick_free_tcp_port_group",
        ),
    )
    for original, replacement, helper_name in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: lifecycle helper rebound: {helper_name}" in violations


def test_ns2_guard_requires_direct_name_calls_for_lifecycle_helpers():
    mutations = (
        ("pick_free_tcp_port_group(2)", "shim.pick_free_tcp_port_group(2)"),
        ("run_and_assert_ok(env, instance_name", "shim.run_and_assert_ok(env, instance_name"),
        ("wait_for_info_protocol(\n", "shim.wait_for_info_protocol(\n"),
        ("capture_alphagsm_stop(\n", "shim.capture_alphagsm_stop(\n"),
        ("wait_for_udp_closed(\"127.0.0.1\"", "shim.wait_for_udp_closed(\"127.0.0.1\""),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: lifecycle helpers must be direct name calls" in violations


def test_ns2_guard_requires_run_commands_to_disable_known_steamcmd_skips():
    mutations = (
        ("allow_known_steamcmd_skip=False", "allow_known_steamcmd_skip=True"),
        (", allow_known_steamcmd_skip=False", ""),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert (
            "fixture.py: run_and_assert_ok must disable known SteamCMD skips"
            in violations
        )


def test_ns2_guard_rejects_conditional_readiness_and_lifecycle_calls():
    mutations = {
        '    run_and_assert_ok(env, instance_name, "create", module_name, allow_known_steamcmd_skip=False)\n': (
            '    if runtime_backend == "docker":\n'
            '        run_and_assert_ok(env, instance_name, "create", module_name, allow_known_steamcmd_skip=False)\n',
            "create",
        ),
        '    run_and_assert_ok(env, instance_name, "setup", "-n", str(selected_port), install_dir, allow_known_steamcmd_skip=False)\n': (
            '    if runtime_backend == "docker":\n'
            '        run_and_assert_ok(env, instance_name, "setup", "-n", str(selected_port), install_dir, allow_known_steamcmd_skip=False)\n',
            "setup",
        ),
        '    run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)\n': (
            '    if runtime_backend == "docker":\n'
            '        run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)\n',
            "start",
        ),
        "        ready_info = wait_for_info_protocol(\n"
        '            env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint\n'
        "        )\n": (
            '        if runtime_backend == "docker":\n'
            "            ready_info = wait_for_info_protocol(\n"
            '                env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint\n'
            "            )\n",
            "readiness",
        ),
        '        run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)\n': (
            '        if runtime_backend == "docker":\n'
            '            run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)\n',
            "status",
        ),
        '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n': (
            '        if runtime_backend == "docker":\n'
            '            query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n',
            "query",
        ),
        '        info_result = run_and_assert_ok(env, instance_name, "info", allow_known_steamcmd_skip=False)\n': (
            '        if runtime_backend == "docker":\n'
            '            info_result = run_and_assert_ok(env, instance_name, "info", allow_known_steamcmd_skip=False)\n',
            "info",
        ),
        '        json_result = run_and_assert_ok(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)\n': (
            '        if runtime_backend == "docker":\n'
            '            json_result = run_and_assert_ok(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)\n',
            "info --json",
        ),
    }
    for original, (replacement, label) in mutations.items():
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: missing unconditional {label}" in violations


def test_ns2_guard_rejects_unchecked_lifecycle_calls():
    asserted_calls = {
        'run_and_assert_ok(env, instance_name, "create", module_name, allow_known_steamcmd_skip=False)': "create",
        'run_and_assert_ok(env, instance_name, "setup", "-n", str(selected_port), install_dir, allow_known_steamcmd_skip=False)': "setup",
        'run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)': "start",
        'run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)': "query",
        'run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)': "status",
        'run_and_assert_ok(env, instance_name, "info", allow_known_steamcmd_skip=False)': "info",
    }
    for asserted_call, command in asserted_calls.items():
        source = NS2_LIFECYCLE_FIXTURE.replace(
            asserted_call,
            asserted_call.replace("run_and_assert_ok", "run_alphagsm"),
            1,
        )

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: {command} must use run_and_assert_ok" in violations

    source = NS2_LIFECYCLE_FIXTURE.replace(
        'run_and_assert_ok(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)',
        'run_alphagsm(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)',
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: info --json must use run_and_assert_ok" in violations


def test_ns2_guard_rejects_wrong_readiness_and_lifecycle_order():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        '        run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)\n'
        '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n'
        '        assert "Server is responding" in query_result.stdout\n',
        '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n'
        '        assert "Server is responding" in query_result.stdout\n'
        '        run_and_assert_ok(env, instance_name, "status", allow_known_steamcmd_skip=False)\n',
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: readiness/status/query/info/info-json are out of order" in violations

    readiness = (
        "        ready_info = wait_for_info_protocol(\n"
        '            env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint\n'
        "        )\n"
    )
    source = NS2_LIFECYCLE_FIXTURE.replace(readiness, "").replace(
        '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n',
        '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n' + readiness,
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: readiness/status/query/info/info-json are out of order" in violations


def test_ns2_guard_rejects_shutdown_before_stop_assertion():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "    assert cleanup_result.returncode == 0, cleanup_result.stderr or cleanup_result.stdout\n"
        '    wait_for_udp_closed("127.0.0.1", a2s_endpoint, STOP_TIMEOUT)\n',
        '    wait_for_udp_closed("127.0.0.1", a2s_endpoint, STOP_TIMEOUT)\n'
        "    assert cleanup_result.returncode == 0, cleanup_result.stderr or cleanup_result.stdout\n",
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: UDP shutdown verification must follow stop assertion" in violations


def test_ns2_guard_rejects_wrong_shutdown_host_or_port():
    mutations = (
        ('"127.0.0.1", a2s_endpoint', '"0.0.0.0", a2s_endpoint'),
        ('"127.0.0.1", a2s_endpoint', '"127.0.0.1", selected_port'),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: UDP shutdown must target localhost and the A2S port" in violations


def test_ns2_guard_rejects_finally_assertion_and_swallowed_lifecycle_error():
    capture = (
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, sys.exc_info()[1]\n"
        "        )\n"
    )
    source = NS2_LIFECYCLE_FIXTURE.replace(
        capture,
        capture + "        assert cleanup_result.returncode == 0\n",
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: finally must only capture AlphaGSM stop" in violations

    source = NS2_LIFECYCLE_FIXTURE.replace(
        "    finally:\n",
        "    except Exception:\n"
        "        pass\n"
        "    finally:\n",
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: lifecycle try must not catch exceptions" in violations


def test_ns2_guard_rejects_raw_stop_and_logging_in_finally():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, sys.exc_info()[1]\n"
        "        )\n",
        '        cleanup_result = run_alphagsm(env, instance_name, "stop")\n'
        '        log_command_result("alphagsm stop", cleanup_result)\n',
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: raw stop/logging in finally is forbidden" in violations


def test_ns2_guard_requires_exact_failure_preserving_stop_capture_shape():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "env, instance_name, sys.exc_info()[1]",
        "env, instance_name, None",
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert (
        "fixture.py: finally must assign exact failure-preserving stop capture"
        in violations
    )


def test_ns2_guard_accepts_unchanged_bound_lifecycle_exception():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, sys.exc_info()[1]\n"
        "        )\n",
        "        lifecycle_error = sys.exc_info()[1]\n"
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, lifecycle_error\n"
        "        )\n",
    )

    assert _ns2_lifecycle_violations(ast.parse(source), "fixture.py") == []


def test_ns2_guard_rejects_rebound_lifecycle_exception_before_capture():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, sys.exc_info()[1]\n"
        "        )\n",
        "        lifecycle_error = sys.exc_info()[1]\n"
        "        lifecycle_error = None\n"
        "        cleanup_result = capture_alphagsm_stop(\n"
        "            env, instance_name, lifecycle_error\n"
        "        )\n",
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert (
        "fixture.py: finally must assign exact failure-preserving stop capture"
        in violations
    )


def test_ns2_guard_rejects_selected_or_a2s_port_mutation_after_definition():
    anchor = "    a2s_endpoint = selected_port + 1\n"
    mutations = (
        "    a2s_endpoint = selected_port\n",
        "    selected_port += 1\n",
        "    del a2s_endpoint\n",
        "    (a2s_endpoint := selected_port)\n",
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(anchor, anchor + mutation)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: selected/A2S port mutated after definition" in violations


def test_ns2_guard_rejects_duplicate_or_extra_lifecycle_calls():
    readiness = (
        "        ready_info = wait_for_info_protocol(\n"
        '            env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint\n'
        "        )\n"
    )
    mutations = (
        (
            '    run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)\n',
            '    run_and_assert_ok(env, instance_name, "start", allow_known_steamcmd_skip=False)\n'
            '    run_alphagsm(env, instance_name, "start")\n',
            "start",
        ),
        (
            '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n',
            '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n'
            '        run_alphagsm(env, instance_name, "query")\n',
            "query",
        ),
        (
            readiness,
            readiness
            + "        second_ready = wait_for_info_protocol(\n"
            + '            env, instance_name, "a2s", START_TIMEOUT, expected_port=a2s_endpoint\n'
            + "        )\n",
            "readiness",
        ),
    )
    for original, replacement, stage in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert f"fixture.py: {stage} lifecycle call must appear exactly once" in violations


def test_ns2_guard_rejects_loop_context_and_handler_port_rebinding():
    anchor = "    a2s_endpoint = selected_port + 1\n"
    mutations = (
        ("    for selected_port in candidate_ports:\n        pass\n", False),
        ("    async for a2s_endpoint in candidate_ports:\n        pass\n", True),
        ("    with port_context() as selected_port:\n        pass\n", False),
        ("    async with port_context() as a2s_endpoint:\n        pass\n", True),
        (
            "    if mutate_port:\n"
            "        try:\n"
            "            raise RuntimeError\n"
            "        except Exception as selected_port:\n"
            "            pass\n",
            False,
        ),
    )
    for mutation, needs_async in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(anchor, anchor + mutation)
        if needs_async:
            source = source.replace(
                "def test_ns2_lifecycle", "async def test_ns2_lifecycle", 1
            )

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: selected/A2S port mutated after definition" in violations


def test_ns2_guard_rejects_import_definition_and_match_port_rebinding():
    anchor = "    a2s_endpoint = selected_port + 1\n"
    mutations = (
        "    import candidate_ports as selected_port\n",
        "    from candidate_ports import query as a2s_endpoint\n",
        "    def selected_port():\n        pass\n",
        "    class a2s_endpoint:\n        pass\n",
        "    match candidate_port:\n        case selected_port:\n            pass\n",
        "    match candidate_port:\n        case [*a2s_endpoint]:\n            pass\n",
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(anchor, anchor + mutation)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: selected/A2S port mutated after definition" in violations


def test_ns2_guard_rejects_unreachable_cleanup_checks_and_stop_rebinding():
    assertion = (
        "    assert cleanup_result.returncode == 0, "
        "cleanup_result.stderr or cleanup_result.stdout\n"
    )
    mutations = (
        "    return\n",
        "    if skip_validation:\n        return\n",
        "    cleanup_result = replacement_result\n",
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(assertion, mutation + assertion)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: stop assertion and closure must be direct and reachable" in violations
        if "cleanup_result = replacement_result" in mutation:
            assert "fixture.py: stop assertion must be an exact direct comparison" in violations


def test_ns2_guard_requires_exact_contextual_stop_assertion():
    assertion = (
        "    assert cleanup_result.returncode == 0, "
        "cleanup_result.stderr or cleanup_result.stdout\n"
    )
    mutations = (
        "    assert cleanup_result.returncode == 0 or True, "
        "cleanup_result.stderr or cleanup_result.stdout\n",
        "    assert 0 == cleanup_result.returncode, "
        "cleanup_result.stderr or cleanup_result.stdout\n",
        "    assert (cleanup_result := replacement_result).returncode == 0, "
        "cleanup_result.stderr or cleanup_result.stdout\n",
        "    assert cleanup_result.returncode == 0\n",
        "    assert cleanup_result.returncode == 0, cleanup_result.stderr\n",
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(assertion, mutation)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: stop assertion must be an exact direct comparison" in violations


def test_ns2_guard_rejects_weakened_or_wrapped_info_assertions():
    mutations = (
        (
            '        assert final_payload["protocol"] == "a2s"\n',
            '        assert final_payload["protocol"] == "a2s" or True\n',
        ),
        (
            '        assert final_payload["port"] == a2s_endpoint\n',
            '        assert bool(final_payload["port"] == a2s_endpoint)\n',
        ),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: final info JSON assertions must be plain exact comparisons" in violations


def test_ns2_guard_rejects_final_info_payload_rebinding_before_assertions():
    parse_line = "        final_payload = json.loads(json_result.stdout.strip())\n"
    source = NS2_LIFECYCLE_FIXTURE.replace(
        parse_line,
        parse_line
        + '        final_payload = {"protocol": "a2s", "port": a2s_endpoint}\n',
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info JSON payload mutated before assertions" in violations


def test_ns2_guard_protects_lifecycle_results_and_parsed_payload():
    mutations = (
        (
            '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n',
            "        query_result = fabricated_result\n",
            "fixture.py: query result mutated before response assertion",
        ),
        (
            '        info_result = run_and_assert_ok(env, instance_name, "info", allow_known_steamcmd_skip=False)\n',
            "        info_result = fabricated_result\n",
            "fixture.py: info result mutated before output assertion",
        ),
        (
            '        json_result = run_and_assert_ok(env, instance_name, "info", "--json", allow_known_steamcmd_skip=False)\n',
            "        json_result = fabricated_result\n",
            "fixture.py: info JSON result mutated before parsing",
        ),
        (
            '        assert final_payload["port"] == a2s_endpoint\n',
            '        final_payload = {"protocol": "a2s", "port": a2s_endpoint}\n',
            "fixture.py: final info JSON payload mutated after parsing",
        ),
    )
    for anchor, mutation, expected in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(anchor, anchor + mutation)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert expected in violations


def test_ns2_guard_requires_exact_plain_info_output_assertion():
    assertion = '        assert "Protocol" in info_result.stdout\n'
    mutations = (
        "",
        '        assert "Protocol" in info_result.stdout or True\n',
        '        assert bool("Protocol" in info_result.stdout)\n',
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(assertion, mutation)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: info output assertion must be an exact plain comparison" in violations


def test_ns2_guard_requires_stdlib_json_loads_for_info_payload():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        "json.loads(json_result.stdout.strip())",
        "fake.loads(json_result.stdout.strip())",
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: final info payload must use exact json.loads" in violations


def test_ns2_guard_protects_exact_json_import_and_binding():
    function_anchor = "def test_ns2_lifecycle(tmp_path):\n"
    mutations = (
        ("import json\n", "import json as payload_json\n"),
        (function_anchor, "json = fake_json\n\n" + function_anchor),
        (
            function_anchor,
            "def test_ns2_lifecycle(tmp_path, json):\n",
        ),
    )
    for original, replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(original, replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: json requires an exact import and no rebinding" in violations


def test_ns2_guard_requires_exact_info_json_parse_expression():
    expression = "json.loads(json_result.stdout.strip())"
    mutations = (
        "json.loads(transform(json_result.stdout.strip()))",
        'json.loads(json_result.stdout.strip() if use_result else "{}")',
        "json.loads(json_result.stdout.strip(), object_hook=fake_hook)",
        "json.loads(fabricated_result.stdout.strip())",
    )
    for mutation in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace(expression, mutation, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: final info payload must use exact json.loads" in violations


def test_ns2_guard_rejects_pytest_skip_and_xfail_lifecycle_escapes():
    anchor = '        query_result = run_and_assert_ok(env, instance_name, "query", allow_known_steamcmd_skip=False)\n'
    for escape in ("skip", "xfail"):
        source = NS2_LIFECYCLE_FIXTURE.replace(
            anchor,
            f'        pytest.{escape}("lifecycle escape")\n' + anchor,
        )

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: lifecycle must not skip or xfail" in violations


def test_ns2_guard_requires_setup_to_use_stringified_selected_port():
    mutations = (
        "str(a2s_endpoint)",
        "selected_port",
        "str(27015)",
    )
    for replacement in mutations:
        source = NS2_LIFECYCLE_FIXTURE.replace("str(selected_port)", replacement, 1)

        violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

        assert "fixture.py: setup must pass str(selected port) after -n" in violations

    source = NS2_LIFECYCLE_FIXTURE.replace(
        '    run_and_assert_ok(env, instance_name, "setup", "-n", str(selected_port), install_dir, allow_known_steamcmd_skip=False)\n',
        '    run_and_assert_ok(\n'
        '        env, instance_name, "setup", "-n", port=str(selected_port),\n'
        '        allow_known_steamcmd_skip=False,\n'
        '    )\n',
    )
    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")
    assert "fixture.py: setup must pass str(selected port) after -n" in violations


def test_ns2_guard_requires_query_response_assertion():
    source = NS2_LIFECYCLE_FIXTURE.replace(
        '        assert "Server is responding" in query_result.stdout\n',
        "",
    )

    violations = _ns2_lifecycle_violations(ast.parse(source), "fixture.py")

    assert "fixture.py: query response assertion is required" in violations


def test_asa_and_astroneer_assert_stop_after_finally_before_shutdown_checks():
    shutdown_helpers = {
        "test_arksurvivalascended.py": {
            "wait_for_generic_udp_closed",
            "wait_for_tcp_closed",
        },
        "test_astroneerserver.py": {"wait_for_generic_udp_closed"},
    }
    for filename, expected_shutdown_helpers in shutdown_helpers.items():
        path = INTEGRATION_TEST_DIR / filename
        lifecycle = _test_function(ast.parse(path.read_text(encoding="utf-8")))
        main_try = next(
            statement for statement in lifecycle.body if isinstance(statement, ast.Try)
        )
        stop_index, stop_result_name = _captured_stop(main_try)
        assert stop_result_name == "stop_result", f"{path}: stop must be captured in finally"
        assert any(
            _call_name(call) == "log_command_result"
            and any(
                isinstance(node, ast.Name) and node.id == stop_result_name
                for node in ast.walk(call)
            )
            for statement in main_try.finalbody[stop_index + 1 :]
            if (call := _direct_call(statement)) is not None
        ), f"{path}: captured stop result must be logged in finally"
        assert not any(
            isinstance(node, ast.Assert)
            for statement in main_try.finalbody
            for node in ast.walk(statement)
        ), f"{path}: stop assertion must not mask the original lifecycle failure"

        try_index = lifecycle.body.index(main_try)
        stop_assert_index = next(
            index
            for index, statement in enumerate(lifecycle.body)
            if index > try_index
            and isinstance(statement, ast.Assert)
            and any(
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "stop_result"
                and node.attr == "returncode"
                for node in ast.walk(statement)
            )
        )
        shutdown_calls = [
            (index, _call_name(_direct_call(statement)))
            for index, statement in enumerate(lifecycle.body)
            if _call_name(_direct_call(statement)) in expected_shutdown_helpers
        ]
        assert {name for _index, name in shutdown_calls} == expected_shutdown_helpers
        assert all(index > stop_assert_index for index, _name in shutdown_calls)


def test_astroneer_requires_game_network_log_before_udp_info_surface():
    path = INTEGRATION_TEST_DIR / "test_astroneerserver.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lifecycle = _test_function(tree)
    calls = [node for node in ast.walk(lifecycle) if isinstance(node, ast.Call)]

    log_ready = next(call for call in calls if _call_name(call) == "wait_for_glob_log_marker")
    info_ready = next(call for call in calls if _call_name(call) == "wait_for_info_protocol")
    query_call = next(call for call in calls if _alphagsm_command(call) == "query")
    info_calls = [call for call in calls if _alphagsm_command(call) == "info"]

    assert "Astro" in ast.unparse(log_ready.args[0])
    assert "Saved" in ast.unparse(log_ready.args[0])
    assert "Logs" in ast.unparse(log_ready.args[0])
    assert _constant_value(_call_argument(log_ready, 1, "glob_pattern")) == "*.log"
    markers = _call_argument(log_ready, 2, "markers")
    assert isinstance(markers, (ast.Tuple, ast.List))
    assert len(markers.elts) == 1
    marker = markers.elts[0]
    assert isinstance(marker, ast.JoinedStr)
    assert "IpNetDriver listening on port" in ast.unparse(marker)
    marker_names = {
        node.id for node in ast.walk(marker) if isinstance(node, ast.Name)
    }
    assert marker_names == {"port"}
    assert log_ready.lineno < info_ready.lineno < query_call.lineno
    assert all(log_ready.lineno < call.lineno for call in info_calls)
    assert _constant_value(_call_argument(info_ready, 2, "expected_protocol")) == "udp"


def test_astroneer_integration_uses_the_managed_registration_endpoint_before_setup():
    path = INTEGRATION_TEST_DIR / "test_astroneerserver.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lifecycle = _test_function(tree)
    calls = [node for node in ast.walk(lifecycle) if isinstance(node, ast.Call)]

    registration_ip = "ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP"
    set_registration_ip = next(
        call
        for call in calls
        if _call_name(call) == "run_and_assert_ok"
        and "registration_publicip" in ast.unparse(call)
    )
    setup_call = next(
        call for call in calls if _call_name(call) == "run_setup_with_port_retry"
    )

    assert registration_ip in text
    assert "pytest.skip" in text
    assert "external IPv4 endpoint" in text
    assert set_registration_ip.lineno < setup_call.lineno


def test_blackops3_generic_udp_query_assertion_matches_alphagsm_output():
    text = (INTEGRATION_TEST_DIR / "test_blackops3server.py").read_text(
        encoding="utf-8"
    )

    assert '"Server port is open (UDP ping on port" in query_result.stdout' in text
    assert '"Server is responding" in query_result.stdout' not in text


def test_rust_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_rust.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_ricochet_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_ricochetserver.py").read_text(
        encoding="utf-8"
    )

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_bmdmserver_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_bmdmserver.py").read_text(
        encoding="utf-8"
    )

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_bdserver_does_not_require_a_host_screen_log_for_docker_readiness():
    text = (INTEGRATION_TEST_DIR / "test_bdserver.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_log_marker" not in text
    assert 'home_dir / "logs"' not in text


def test_proton_docker_tests_do_not_require_host_only_readiness_surfaces():
    for filename in (
        "test_empyrionserver.py",
        "test_mythofempiresserver.py",
        "test_reignofdwarfserver.py",
        "test_remnantsserver.py",
    ):
        text = (INTEGRATION_TEST_DIR / filename).read_text(encoding="utf-8")

        assert "wait_for_info_protocol" in text
        assert "wait_for_log_marker" not in text


def test_xonotic_uses_alphagsm_info_instead_of_raw_quake_readiness():
    text = (INTEGRATION_TEST_DIR / "test_xntserver.py").read_text(encoding="utf-8")

    assert "wait_for_info_protocol" in text
    assert "wait_for_quake_ready" not in text


def test_docker_lanes_require_docker_directly():
    routing = runpy.run_path("scripts/ci_game_test_routing.py")
    docker_default_tests = routing["DOCKER_DEFAULT_RUNTIME_TESTS"]
    offenders = []
    for test_path in sorted(docker_default_tests):
        path = Path(test_path)
        if path.name in SPECIAL_CASES:
            continue
        text = path.read_text(encoding="utf-8")
        if 'require_command("docker")' not in text:
            offenders.append(f"{path}: missing direct Docker requirement")
        if re.search(r"require_command_for_runtime\(\s*[\"']docker[\"']", text):
            offenders.append(f"{path}: Docker passed to process-only helper")

    assert offenders == []


def test_readyornot_uses_game_log_and_current_udp_health_surface():
    integration_text = (INTEGRATION_TEST_DIR / "test_readyornotserver.py").read_text(
        encoding="utf-8"
    )
    smoke_text = Path("tests/smoke_tests/run_readyornotserver.sh").read_text(
        encoding="utf-8"
    )

    assert '"ReadyOrNot" / "Saved" / "Logs" / "ReadyOrNot.log"' in integration_text
    assert "wait_for_log_marker" in integration_text
    assert 'wait_for_info_protocol(env, server_name, "udp"' in integration_text
    assert '"a2s"' not in integration_text
    assert "ReadyOrNot/Saved/Logs/ReadyOrNot.log" in smoke_text
    assert 'wait_for_info_protocol "$SERVER_NAME" "udp"' in smoke_text
    assert '"a2s"' not in smoke_text


def test_returntomoria_uses_status_json_before_alphagsm_info_readiness():
    text = (INTEGRATION_TEST_DIR / "test_returntomoriaserver.py").read_text(
        encoding="utf-8"
    )

    status_wait = text.index("status_payload = wait_for_status_json_running(")
    info_wait = text.index("info_data = wait_for_info_protocol(")

    assert status_wait < info_wait
    assert 'safe_status.get("Status") == "running"' in text
    assert "return safe_status" in text
    assert "return payload" not in text
    assert "wait_for_info_protocol" in text
    assert "wait_for_udp_open" not in text


def test_returntomoria_wakes_the_enabled_console_before_status_readiness():
    text = (INTEGRATION_TEST_DIR / "test_returntomoriaserver.py").read_text(
        encoding="utf-8"
    )

    start = text.index('run_and_assert_ok(env, server_name, "start")')
    wake = text.index('run_and_assert_ok(env, server_name, "send", " ")')
    status_wait = text.index("status_payload = wait_for_status_json_running(")

    assert start < wake < status_wait


def test_theforest_shutdown_proves_selected_a2s_query_endpoint_closed():
    path = INTEGRATION_TEST_DIR / "test_theforestserver.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = _top_level_imports(path)
    assert ("wait_for_udp_closed", "conftest") in imports
    assert ("wait_for_tcp_closed", "conftest") not in imports
    assert ("json", None) in imports
    shutdown_imports = [
        (node.module, alias.name, alias.asname)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name in {"wait_for_udp_closed", "wait_for_tcp_closed"}
        or alias.asname in {"wait_for_udp_closed", "wait_for_tcp_closed"}
    ]
    assert shutdown_imports == [("conftest", "wait_for_udp_closed", None)]
    assert not any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and node.id in {"wait_for_udp_closed", "wait_for_tcp_closed"}
        for node in ast.walk(tree)
    ), f"{path}: shutdown helpers must not be rebound"
    lifecycle = _test_function(tree)
    main_try = next(
        statement for statement in lifecycle.body if isinstance(statement, ast.Try)
    )
    try_index = lifecycle.body.index(main_try)

    dump_entries = [
        (index, result_name)
        for index, statement in enumerate(lifecycle.body[:try_index])
        for result_name, call in [_direct_assigned_call(statement)]
        if result_name and _alphagsm_command(call) == "dump"
    ]
    assert len(dump_entries) == 1, f"{path}: select queryport from one direct dump"
    dump_index, dump_result_name = dump_entries[0]

    query_port_entries = []
    for index, statement in enumerate(lifecycle.body[dump_index + 1 : try_index]):
        query_port_name, int_call = _direct_assigned_call(statement)
        if _call_name(int_call) != "int" or len(int_call.args) != 1:
            continue
        queryport_lookup = int_call.args[0]
        if _mapping_key(queryport_lookup) != "queryport":
            continue
        loads_call = queryport_lookup.value
        loads_argument = _call_argument(loads_call, 0, "s")
        if not (
            _call_name(loads_call) == "loads"
            and isinstance(loads_call.func, ast.Attribute)
            and isinstance(loads_call.func.value, ast.Name)
            and loads_call.func.value.id == "json"
            and isinstance(loads_argument, ast.Attribute)
            and loads_argument.attr == "stdout"
            and isinstance(loads_argument.value, ast.Name)
            and loads_argument.value.id == dump_result_name
        ):
            continue
        query_port_entries.append((index, query_port_name))

    assert query_port_entries == [(0, "query_port")], (
        f"{path}: query_port must come directly from dump['queryport']"
    )
    assert not any(
        _statement_mutates_name(statement, "query_port")
        for statement in lifecycle.body[dump_index + 2 :]
    ), f"{path}: selected query_port must not be rebound"

    calls = [node for node in ast.walk(lifecycle) if isinstance(node, ast.Call)]
    assert not any(_call_name(call) == "wait_for_tcp_closed" for call in calls), (
        f"{path}: main TCP closure is not A2S shutdown proof"
    )

    post_try = lifecycle.body[try_index + 1 :]
    shutdown_calls = [
        _direct_call(statement)
        for statement in post_try
        if _call_name(_direct_call(statement)) == "wait_for_udp_closed"
    ]
    assert len(shutdown_calls) == 1, f"{path}: require one direct A2S closure check"
    shutdown_call = shutdown_calls[0]
    assert (
        _constant_value(_call_argument(shutdown_call, 0, "host")) == "127.0.0.1"
        and isinstance(_call_argument(shutdown_call, 1, "port"), ast.Name)
        and _call_argument(shutdown_call, 1, "port").id == "query_port"
        and isinstance(_call_argument(shutdown_call, 2, "timeout_seconds"), ast.Name)
        and _call_argument(shutdown_call, 2, "timeout_seconds").id == "STOP_TIMEOUT"
    ), f"{path}: shutdown must target the exact selected A2S query endpoint"


@pytest.mark.parametrize(
    "filename",
    ("test_returntomoriaserver.py", "test_theforestserver.py"),
)
def test_moria_and_forest_start_once_inside_failure_preserving_cleanup(filename):
    path = INTEGRATION_TEST_DIR / filename
    lifecycle = _test_function(ast.parse(path.read_text(encoding="utf-8")))
    lifecycle_tries = [
        statement
        for statement in lifecycle.body
        if isinstance(statement, ast.Try)
        and not statement.handlers
        and not statement.orelse
        and statement.finalbody
    ]
    start_calls = [
        call
        for call in ast.walk(lifecycle)
        if isinstance(call, ast.Call) and _alphagsm_command(call) == "start"
    ]

    assert len(lifecycle_tries) == 1, f"{path}: expected one failure-preserving try"
    assert len(start_calls) == 1, f"{path}: start must appear exactly once"
    protected_try = lifecycle_tries[0]
    first_call = _direct_call(protected_try.body[0])
    assert first_call is start_calls[0], f"{path}: start must be first in protected try"
    assert _call_name(first_call) == "run_and_assert_ok"


def test_iosserver_lifecycle_is_gated_on_provider_authentication():
    text = (INTEGRATION_TEST_DIR / "test_iosserver.py").read_text(
        encoding="utf-8"
    )

    assert "pytest.mark.skip" in text
    assert "ENABLED (AUTH)" in text


def test_integration_tests_do_not_permanently_skip_download_or_timeout_failures():
    """Download and timeout failures must remain visible to CI."""

    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if re.search(r"pytest\.mark\.skip[^\n]*(download|timeout)", text, re.IGNORECASE):
            offenders.append(str(path))

    assert offenders == []


def test_ss14_integration_supports_byo_archive_url_without_hiding_download_failures():
    text = SS14_INTEGRATION_TEST.read_text(encoding="utf-8")

    assert "ALPHAGSM_SS14_SERVER_URL" in text
    assert "BYO_SKIP_REASON" in text
    assert "skip_for_known_steamcmd_issue(result)" in text
    assert 'pytest.mark.skip' not in text
