#!/usr/bin/env python3
"""Generate comprehensive unit tests for all game modules to achieve 100% coverage.

Uses AST parsing to extract function bodies and regex to find all server.data
access patterns, ensuring generated tests provide all needed data fields.
"""

import ast
import os
import re
import textwrap

GAMEMODULES_DIR = "src/gamemodules"
TESTS_DIR = "tests/gamemodules"
VALVE_MODULES = set()


def _top_level_module_entries():
    entries = []
    for name in sorted(os.listdir(GAMEMODULES_DIR)):
        path = os.path.join(GAMEMODULES_DIR, name)
        if os.path.isfile(path) and name.endswith(".py") and name != "__init__.py":
            entries.append((name[:-3], path))
            continue
        if not os.path.isdir(path) or name == "__pycache__":
            continue
        main_path = os.path.join(path, "main.py")
        init_path = os.path.join(path, "__init__.py")
        if os.path.isfile(main_path):
            entries.append((name, main_path))
        elif os.path.isfile(init_path):
            entries.append((name, init_path))
    return entries


def find_valve_modules():
    """Find all modules that use define_valve_server_module."""
    for modname, fpath in _top_level_module_entries():
        with open(fpath) as f:
            src = f.read()
        if "define_valve_server_module" in src:
            VALVE_MODULES.add(modname)


def get_function_source(source, funcname):
    """Extract the source lines of a function by name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else len(lines)
            return "\n".join(lines[start:end])
    return ""


def find_data_keys(func_source):
    """Find all server.data["key"] and server.data['key'] and .get("key",...) accesses."""
    keys = set()
    # server.data["key"] or server.data['key']
    for m in re.finditer(r'server\.data\[(["\'])(\w+)\1\]', func_source):
        keys.add(m.group(2))
    # server.data.get("key", ...) or .setdefault("key", ...)
    for m in re.finditer(r'server\.data\.(?:get|setdefault)\((["\'])(\w+)\1', func_source):
        keys.add(m.group(2))
    return keys


def count_input_calls(func_source):
    """Count number of input() calls in function source."""
    return len(re.findall(r'\binput\s*\(', func_source))


def get_function_names(source):
    """Get all top-level function names from module source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [node.name for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.FunctionDef)]


def guess_value_for_key(key):
    """Guess a reasonable test value for a data key."""
    int_keys = {
        "port", "queryport", "maxplayers", "updateport", "peerport",
        "filetransferport", "playercount", "rconport", "gameport",
        "slots", "serverport", "webadminport", "steamport",
        "rawport", "beaconport",
    }
    bool_keys = {
        "license_accepted", "public", "publiclobby", "visible",
        "crossplay", "multithreading", "upnp",
    }
    if key in int_keys:
        return "27015"
    if key in bool_keys:
        return "True"
    return '"test"'


def parse_module(fpath):
    """Parse a game module and extract comprehensive properties."""
    with open(fpath) as f:
        source = f.read()

    # Skip aliases and stubs
    if "ALIAS_TARGET" in source:
        return None
    if "raise NotImplementedError" in source and "def configure" not in source:
        return None

    funcs = get_function_names(source)
    if not funcs or "configure" not in funcs:
        return None

    info = {
        "source": source,
        "functions": funcs,
        "uses_steamcmd": "steamcmd" in source and "install_archive" not in source,
        "is_archive": "install_archive" in source,
        "has_compression": "_compression" in source,
        "has_resolve": "resolve_download" in funcs,
    }

    # Extract configure signature details
    configure_src = get_function_source(source, "configure")
    info["configure_input_count"] = count_input_calls(configure_src)
    info["configure_has_ask"] = "if ask:" in configure_src or "if ask :" in configure_src
    info["configure_data_keys"] = find_data_keys(configure_src)

    # Extract configure function kwargs using AST
    configure_params = set()
    try:
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "configure":
                for arg in node.args.args + node.args.kwonlyargs:
                    configure_params.add(arg.arg)
                break
    except SyntaxError:
        pass
    info["configure_params"] = configure_params

    # Detect if module has any resolve_download calls (in configure or standalone)
    info["needs_url"] = ("url" in configure_params or
                          "resolve_download" in source or
                          info["is_archive"])
    info["needs_download_name"] = "download_name" in configure_params or info["is_archive"]
    info["needs_version"] = "version" in configure_params

    # Detect if configure calls a resolve function unconditionally (not gated by ask)
    # Pattern: "if url is None:\n    ..., ... = resolve_..."
    info["configure_resolve_func"] = None
    resolve_calls = re.findall(r'(\w*resolve\w+)\(', configure_src)
    if resolve_calls:
        # Check if this is unconditional (just "if url is None:", not "if ask and url is None:")
        if re.search(r'if url is None:\s*\n\s*\w+.*?(?:resolve\w+)\(', configure_src) and \
           not re.search(r'if ask.*url is None:\s*\n\s*\w+.*?(?:resolve\w+)\(', configure_src):
            info["configure_resolve_func"] = resolve_calls[0]

    # Check if port is used at all
    info["has_port"] = "port" in info["configure_data_keys"] or "'port'" in configure_src or '"port"' in configure_src

    # Extract get_start_command data keys
    gsc_src = get_function_source(source, "get_start_command")
    info["gsc_data_keys"] = find_data_keys(gsc_src)
    # Also check for os.path.isfile or ServerError in get_start_command
    info["gsc_has_exe_check"] = "ServerError" in gsc_src or "os.path.isfile" in gsc_src
    info["gsc_has_exe_check_raise"] = "raise ServerError" in gsc_src or "raise  ServerError" in gsc_src

    # Extract exe_name default
    m = re.search(r'exe_name\s*=\s*["\']([^"\']*)["\']', source)
    info["exe_name"] = m.group(1) if m else "server"

    # Extract default port
    m = re.search(r'server\.data\.(?:get|setdefault)\(["\']port["\']\s*,\s*(\d+)\)', source)
    info["default_port"] = int(m.group(1)) if m else None

    # Extract steam_app_id
    m = re.search(r'^steam_app_id\s*=\s*(\d+)', source, re.MULTILINE)
    info["steam_app_id"] = int(m.group(1)) if m else 0

    # Extract stop command
    m = re.search(r'send_to_server\(server\.name,\s*["\']([^"\']*)["\']', source)
    info["stop_cmd"] = m.group(1) if m else None

    # Check if do_stop raises ServerError
    do_stop_src = get_function_source(source, "do_stop")
    info["do_stop_raises"] = "raise ServerError" in do_stop_src

    # Parse checkvalue int/str/backup keys
    cv_src = get_function_source(source, "checkvalue")
    info["checkvalue_int_keys"] = []
    info["checkvalue_str_keys"] = []
    info["checkvalue_bool_keys"] = []
    info["checkvalue_has_backup"] = "backup" in cv_src and "key[0]" in cv_src

    # Parse checkvalue patterns - look for return int(...) and return str(...)
    # Pattern: if key[0] == "X": or if key[0] in ("X", "Y"):
    # Followed by return int(...) or return str(...)
    for m in re.finditer(
        r'(?:el)?if\s+key\[0\]\s*(?:==\s*["\'](\w+)["\']|in\s*\(([^)]+)\))\s*:'
        r'(.*?)(?=(?:el)?if\s+key\[0\]|raise\s+ServerError|$)',
        cv_src, re.DOTALL
    ):
        single_key, multi_keys, body = m.groups()
        keys_found = []
        if single_key and single_key != "backup":
            keys_found.append(single_key)
        if multi_keys:
            keys_found.extend(k for k in re.findall(r'["\'](\w+)["\']', multi_keys) if k != "backup")

        if "return int(" in body or "return  int(" in body:
            info["checkvalue_int_keys"].extend(keys_found)
        elif "return str(" in body or "return  str(" in body:
            info["checkvalue_str_keys"].extend(keys_found)
        elif "return bool(" in body or "return  bool(" in body:
            # Treat bool keys as str for testing purposes
            info["checkvalue_str_keys"].extend(keys_found)

    # Check for publiclobby or other non-standard checkvalue return types
    # Also detect bool returns like: return value[0].lower() in ("true", "1", ...)
    # or return bool(...) or ternary bool patterns
    for m_bool in re.finditer(
        r'(?:el)?if\s+key\[0\]\s*(?:==\s*["\'](\w+)["\']|in\s*\(([^)]+)\))\s*:'
        r'(.*?)(?=(?:el)?if\s+key\[0\]|raise\s+ServerError|$)',
        cv_src, re.DOTALL
    ):
        single_key, multi_keys, body = m_bool.groups()
        keys_found = []
        if single_key and single_key != "backup":
            keys_found.append(single_key)
        if multi_keys:
            keys_found.extend(k for k in re.findall(r'["\'](\w+)["\']', multi_keys) if k != "backup")
        # Check for bool-ish returns
        if any(k not in info["checkvalue_int_keys"] and k not in info["checkvalue_str_keys"] for k in keys_found):
            if ("lower()" in body or "True" in body or "False" in body or
                    "bool(" in body):
                for k in keys_found:
                    if k not in info["checkvalue_int_keys"] and k not in info["checkvalue_str_keys"]:
                        info["checkvalue_bool_keys"].append(k)

    return info


def build_mock_dict(source):
    """Determine which modules need mocking based on imports."""
    mocks = {"screen": "MagicMock()"}

    if "steamcmd" in source and "install_archive" not in source:
        mocks["utils.steamcmd"] = "MagicMock()"
    if "install_archive" in source:
        mocks["utils.archive_install"] = "MagicMock()"
    if "backups" in source or "backup" in source:
        mocks["utils.backups.backups"] = "MagicMock()"
        mocks["utils.backups"] = "MagicMock()"
    if "downloader" in source:
        mocks["downloader"] = "MagicMock()"
    if "github_releases" in source:
        mocks["utils.github_releases"] = "MagicMock()"
    if "fileutils" in source:
        mocks["utils.fileutils"] = "MagicMock()"

    return mocks


def generate_test(modname, info):
    """Generate test code for a game module."""
    source = info["source"]
    funcs = info["functions"]
    port = info["default_port"] or 27015
    exe = info["exe_name"]

    mocks = build_mock_dict(source)
    mock_str = ", ".join(f"'{k}': {v}" for k, v in sorted(mocks.items()))

    lines = []
    lines.append(f'"""Full coverage tests for {modname}."""\n')
    lines.append("import os")
    lines.append("from unittest.mock import patch, MagicMock\n")
    lines.append("import pytest\n")

    # Module import with mocks + ServerError import inside with block
    has_server_error = "ServerError" in source
    lines.append(f"with patch.dict('sys.modules', {{{mock_str}}}):")
    lines.append(f"    import gamemodules.{modname} as mod")
    if has_server_error:
        lines.append("    from server import ServerError")
    lines.append("\n")

    # DummyData and DummyServer
    lines.append(textwrap.dedent("""\
        class DummyData(dict):
            def save(self):
                pass
            def setdefault(self, key, value=None):
                if key not in self:
                    self[key] = value
                return self[key]
            def get(self, key, default=None):
                return super().get(key, default)


        class DummyServer:
            def __init__(self, name="testserver"):
                self.name = name
                self.data = DummyData()
                self._stopped = False
                self._started = False
            def stop(self):
                self._stopped = True
            def start(self):
                self._started = True
    """))

    # Helper to add data setup for a function
    def data_setup_lines(keys, prefix="    ", use_tmp_path=True):
        result = []
        for key in sorted(keys):
            if key in ("dir", "exe_name"):
                continue  # handled separately
            val = guess_value_for_key(key)
            result.append(f'{prefix}server.data["{key}"] = {val}')
        return result

    # ============ configure tests ============
    # Test configure(ask=False)
    lines.append("\ndef test_configure_basic(tmp_path):")
    lines.append("    server = DummyServer()")

    # Build kwargs
    kwargs = f"port={port}, dir=str(tmp_path)"
    if info["needs_url"]:
        kwargs += ', url="https://example.com/test.zip"'
    if info["needs_download_name"]:
        kwargs += ', download_name="test.zip"'
    if info["needs_version"]:
        kwargs += ', version="1.0"'

    lines.append(f"    mod.configure(server, ask=False, {kwargs})")
    if info["has_port"]:
        lines.append(f"    assert server.data['port'] == {port}")
    lines.append("")

    # Test configure(ask=True) with defaults
    if info["configure_has_ask"]:
        input_count = info["configure_input_count"]
        resolve_func = info["configure_resolve_func"]

        lines.append("\ndef test_configure_ask_defaults(tmp_path, monkeypatch):")
        lines.append('    monkeypatch.setattr("builtins.input", lambda prompt: "")')
        lines.append("    server = DummyServer()")
        # Pre-populate data so empty inputs use existing defaults
        if info["has_port"]:
            lines.append(f'    server.data["port"] = {port}')
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        if info["needs_url"]:
            lines.append('    server.data["url"] = "https://example.com/test.zip"')
        if info["needs_download_name"]:
            lines.append('    server.data["download_name"] = "test.zip"')
        # Pre-populate any other configure data keys
        for key in sorted(info["configure_data_keys"]):
            if key in ("dir", "exe_name", "port", "url", "download_name", "backup", "backupfiles"):
                continue
            val = guess_value_for_key(key)
            lines.append(f'    server.data["{key}"] = {val}')
        if resolve_func:
            lines.append(f"    with patch.object(mod, '{resolve_func}', return_value=('1.0', 'https://example.com/dl.zip')):")
            lines.append("        mod.configure(server, ask=True)")
        else:
            lines.append("    mod.configure(server, ask=True)")
        lines.append("")

        # Test configure(ask=True) with custom values
        lines.append("\ndef test_configure_ask_custom(tmp_path, monkeypatch):")
        # Provide enough inputs for all input() calls
        input_values = []
        if info["has_port"]:
            input_values.append(f'"{port + 1}"')
        input_values.append("str(tmp_path / 'custom')")
        # Modules that prompt for URL
        if info["needs_url"] and "url" in info["configure_data_keys"]:
            input_values.append('"https://example.com/new.tar.gz"')
        # Pad with empty strings for any extra inputs
        while len(input_values) < input_count:
            input_values.append('""')

        # Build the inputs list as Python code
        if len(input_values) <= 3:
            vals = ", ".join(input_values)
            lines.append(f"    inputs = iter([{vals}])")
        else:
            lines.append("    inputs = iter([")
            for v in input_values:
                lines.append(f"        {v},")
            lines.append("    ])")
        lines.append('    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))')
        lines.append("    server = DummyServer()")
        if info["needs_url"]:
            lines.append('    server.data["url"] = "https://example.com/test.zip"')
        if info["needs_download_name"]:
            lines.append('    server.data["download_name"] = "test.zip"')
        if resolve_func:
            lines.append(f"    with patch.object(mod, '{resolve_func}', return_value=('1.0', 'https://example.com/dl.zip')):")
            lines.append("        mod.configure(server, ask=True)")
        else:
            lines.append("    mod.configure(server, ask=True)")
        lines.append("")

    # ============ install test ============
    if "install" in funcs:
        lines.append("\ndef test_install(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        lines.append(f'    server.data["exe_name"] = "{exe}"')
        if info["uses_steamcmd"]:
            lines.append(f'    server.data["Steam_AppID"] = {info["steam_app_id"]}')
            lines.append('    server.data["Steam_anonymous_login_possible"] = True')
        if info["needs_url"]:
            lines.append('    server.data["url"] = "https://example.com/test.zip"')
        if info["needs_download_name"]:
            lines.append('    server.data["download_name"] = "test.zip"')
        # Add any other install-time data keys
        install_src = get_function_source(source, "install")
        for key in sorted(find_data_keys(install_src)):
            if key in ("dir", "exe_name", "Steam_AppID", "Steam_anonymous_login_possible", "url", "download_name"):
                continue
            val = guess_value_for_key(key)
            lines.append(f'    server.data["{key}"] = {val}')
        lines.append("    mod.install(server)")
        lines.append("")

    # ============ update test ============
    if "update" in funcs:
        lines.append("\ndef test_update_with_restart(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        if info["uses_steamcmd"]:
            lines.append(f'    server.data["Steam_AppID"] = {info["steam_app_id"]}')
            lines.append('    server.data["Steam_anonymous_login_possible"] = True')
        lines.append("    mod.update(server, validate=True, restart=True)")
        lines.append("    assert server._stopped")
        lines.append("    assert server._started")
        lines.append("")

        lines.append("\ndef test_update_no_restart(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        if info["uses_steamcmd"]:
            lines.append(f'    server.data["Steam_AppID"] = {info["steam_app_id"]}')
            lines.append('    server.data["Steam_anonymous_login_possible"] = True')
        lines.append("    mod.update(server, validate=False, restart=False)")
        lines.append("    assert server._stopped")
        lines.append("    assert not server._started")
        lines.append("")

        lines.append("\ndef test_update_stop_exception(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        if info["uses_steamcmd"]:
            lines.append(f'    server.data["Steam_AppID"] = {info["steam_app_id"]}')
            lines.append('    server.data["Steam_anonymous_login_possible"] = True')
        lines.append("    server.stop = MagicMock(side_effect=Exception('already stopped'))")
        lines.append("    mod.update(server, validate=False, restart=False)")
        lines.append("")

    # ============ restart test ============
    if "restart" in funcs:
        lines.append("\ndef test_restart():")
        lines.append("    server = DummyServer()")
        lines.append("    mod.restart(server)")
        lines.append("    assert server._stopped")
        lines.append("    assert server._started")
        lines.append("")

    # ============ get_start_command test ============
    if "get_start_command" in funcs:
        gsc_keys = info["gsc_data_keys"]

        lines.append("\ndef test_get_start_command(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        lines.append(f'    server.data["exe_name"] = "{exe}"')

        # Create exe file (handle subdirectory paths)
        if "/" in exe:
            lines.append(f'    exe_path = tmp_path / "{exe}"')
            lines.append("    exe_path.parent.mkdir(parents=True, exist_ok=True)")
            lines.append('    exe_path.write_text("")')
        else:
            lines.append(f'    (tmp_path / "{exe}").write_text("")')

        # Add all needed data fields
        for key in sorted(gsc_keys):
            if key in ("dir", "exe_name"):
                continue
            val = guess_value_for_key(key)
            lines.append(f'    server.data["{key}"] = {val}')

        lines.append("    cmd, cwd = mod.get_start_command(server)")
        lines.append("    assert isinstance(cmd, list)")
        lines.append("")

        # Test missing exe (only if module actually checks)
        if info["gsc_has_exe_check"] and has_server_error:
            lines.append("\ndef test_get_start_command_missing_exe(tmp_path):")
            lines.append("    server = DummyServer()")
            lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
            lines.append(f'    server.data["exe_name"] = "nonexistent"')
            for key in sorted(gsc_keys):
                if key in ("dir", "exe_name"):
                    continue
                val = guess_value_for_key(key)
                lines.append(f'    server.data["{key}"] = {val}')
            lines.append("    with pytest.raises(ServerError):")
            lines.append("        mod.get_start_command(server)")
            lines.append("")

    # ============ do_stop test ============
    if "do_stop" in funcs:
        if info["do_stop_raises"]:
            lines.append("\ndef test_do_stop_raises():")
            lines.append("    server = DummyServer()")
            lines.append("    with pytest.raises(ServerError):")
            lines.append("        mod.do_stop(server, 0)")
        else:
            lines.append("\ndef test_do_stop():")
            lines.append("    server = DummyServer()")
            lines.append("    mod.do_stop(server, 0)")
            lines.append("    mod.screen.send_to_server.assert_called()")
        lines.append("")

    # ============ status test ============
    if "status" in funcs:
        lines.append("\ndef test_status():")
        lines.append("    server = DummyServer()")
        lines.append("    mod.status(server, verbose=True)")
        lines.append("")

    # ============ message test ============
    if "message" in funcs:
        lines.append("\ndef test_message():")
        lines.append("    server = DummyServer()")
        lines.append('    mod.message(server, "hello")')
        lines.append("")

    # ============ backup test ============
    if "backup" in funcs:
        lines.append("\ndef test_backup():")
        lines.append("    server = DummyServer()")
        lines.append('    server.data["dir"] = "/tmp/test/"')
        lines.append('    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}')
        lines.append("    mod.backup(server)")
        lines.append("")

    # ============ prestart test ============
    if "prestart" in funcs:
        prestart_src = get_function_source(source, "prestart")
        prestart_keys = find_data_keys(prestart_src)
        lines.append("\ndef test_prestart(tmp_path):")
        lines.append("    server = DummyServer()")
        lines.append(f'    server.data["dir"] = str(tmp_path) + "/"')
        for key in sorted(prestart_keys):
            if key == "dir":
                continue
            val = guess_value_for_key(key)
            lines.append(f'    server.data["{key}"] = {val}')
        lines.append("    mod.prestart(server)")
        lines.append("")

    # ============ checkvalue tests ============
    if "checkvalue" in funcs:
        if has_server_error:
            # Empty key
            lines.append("\ndef test_checkvalue_empty_key():")
            lines.append("    server = DummyServer()")
            lines.append("    with pytest.raises(ServerError):")
            lines.append("        mod.checkvalue(server, ())")
            lines.append("")

            # Unsupported key
            lines.append("\ndef test_checkvalue_unsupported_key():")
            lines.append("    server = DummyServer()")
            lines.append("    with pytest.raises(ServerError):")
            lines.append('        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")')
            lines.append("")

            # No value
            test_key = (info["checkvalue_int_keys"] or info["checkvalue_str_keys"] or [None])[0]
            if test_key:
                lines.append("\ndef test_checkvalue_no_value():")
                lines.append("    server = DummyServer()")
                lines.append("    with pytest.raises(ServerError):")
                lines.append(f'        mod.checkvalue(server, ("{test_key}",))')
                lines.append("")

        # Int keys
        for key in info["checkvalue_int_keys"]:
            lines.append(f'\ndef test_checkvalue_{key}():')
            lines.append("    server = DummyServer()")
            lines.append(f'    result = mod.checkvalue(server, ("{key}",), "12345")')
            lines.append("    assert result == 12345")
            lines.append("")

        # Str keys
        for key in info["checkvalue_str_keys"]:
            safe_key = key.replace("-", "_")
            lines.append(f'\ndef test_checkvalue_{safe_key}():')
            lines.append("    server = DummyServer()")
            lines.append(f'    result = mod.checkvalue(server, ("{key}",), "/test/value")')
            lines.append(f'    assert result == "/test/value"')
            lines.append("")

        # Bool keys
        for key in info["checkvalue_bool_keys"]:
            safe_key = key.replace("-", "_")
            lines.append(f'\ndef test_checkvalue_{safe_key}():')
            lines.append("    server = DummyServer()")
            lines.append(f'    result = mod.checkvalue(server, ("{key}",), "true")')
            lines.append(f"    assert result is True or result == 'true'")
            lines.append("")

        # Backup key
        if info["checkvalue_has_backup"]:
            lines.append("\ndef test_checkvalue_backup():")
            lines.append("    server = DummyServer()")
            lines.append('    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}')
            lines.append('    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")')
            lines.append("")

    # ============ _compression tests (archive modules) ============
    if info["has_compression"]:
        lines.append('\ndef test_compression_zip():')
        lines.append("    server = DummyServer()")
        lines.append('    server.data["download_name"] = "test.zip"')
        lines.append('    assert mod._compression(server) == "zip"')
        lines.append("")

        lines.append('\ndef test_compression_tar_gz():')
        lines.append("    server = DummyServer()")
        lines.append('    server.data["download_name"] = "test.tar.gz"')
        lines.append('    result = mod._compression(server)')
        lines.append('    assert result in ("tar.gz", "gz")')
        lines.append("")

        if has_server_error:
            lines.append('\ndef test_compression_invalid():')
            lines.append("    server = DummyServer()")
            lines.append('    server.data["download_name"] = "test.xyz_unknown"')
            lines.append("    with pytest.raises(ServerError):")
            lines.append("        mod._compression(server)")
            lines.append("")

    # ============ resolve_download test ============
    # resolve_download functions make HTTP calls - tested separately with proper HTTP mocking

    return "\n".join(lines) + "\n"


def main():
    find_valve_modules()
    print(f"Found {len(VALVE_MODULES)} valve modules (skipping)")

    os.makedirs(TESTS_DIR, exist_ok=True)

    generated = 0
    skipped = 0

    for modname, fpath in _top_level_module_entries():
        if modname in VALVE_MODULES:
            skipped += 1
            continue

        info = parse_module(fpath)
        if info is None:
            skipped += 1
            continue

        test_code = generate_test(modname, info)
        test_fpath = os.path.join(TESTS_DIR, f"test_{modname}_cov.py")
        with open(test_fpath, "w") as f:
            f.write(test_code)
        generated += 1

    print(f"Generated: {generated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
