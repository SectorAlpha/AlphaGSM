#!/usr/bin/env python3
"""Apply Wine/Proton support to Windows-only game server modules.

This script performs three categories of transformations on each module:
1. Adds 'import utils.proton as proton' and 'from utils.platform_info import IS_LINUX'
2. Adds force_windows=IS_LINUX to steamcmd.download() calls in install() and update()
3. Transforms get_start_command() to wrap the exe with proton on Linux

Usage: python3 scripts/apply_proton_support.py [--dry-run]
"""

import re
import sys

MODULES = [
    "darkandlightserver",
    "fearthenightserver",
    "groundbranchserver",
    "motortownserver",
    "mythofempiresserver",
    "notdserver",
    "rs2server",
    "scumserver",
    "subsistenceserver",
    "remnantsserver",
    "askaserver",
    "astroneerserver",
    "battlecryoffreedomserver",
    "blackops3server",
    "blackwakeserver",
    "ducksideserver",
    "empyrionserver",
    "heatserver",
    "hellletlooseserver",
    "icarusserver",
    "lifeisfeudalserver",
    "medievalengineersserver",
    "miscreatedserver",
    "mw3server",
    "noonesurvivedserver",
    "outpostzeroserver",
    "pixarkserver",
    "primalcarnageextinctionserver",
    "readyornotserver",
    "reignofdwarfserver",
    "reignofkingsserver",
    "returntomoriaserver",
    "ror2server",
    "arksurvivalascended",
    "saleblazersserver",
    "sniperelite4server",
    "sonsoftheforestserver",
    "starruptureserver",
    "staxelserver",
    "sunkenlandserver",
    "terratechworldsserver",
    "theforestserver",
]

# Proton wrapping block to insert before the return in get_start_command
PROTON_BLOCK = (
    "    if IS_LINUX:\n"
    "        cmd = proton.wrap_command(cmd,"
    " wineprefix=server.data.get(\"wineprefix\"))\n"
)

DRY_RUN = "--dry-run" in sys.argv


def add_imports(content):
    """Add proton import after steamcmd import, and IS_LINUX before steam_app_id."""
    # Add proton import right before steamcmd import (keeps alphabetical order)
    if "import utils.proton as proton" not in content:
        content = content.replace(
            "import utils.steamcmd as steamcmd\n",
            "import utils.proton as proton\nimport utils.steamcmd as steamcmd\n",
            1,
        )

    # Add IS_LINUX import right before the 'steam_app_id = ' line
    if "from utils.platform_info import IS_LINUX" not in content:
        content = content.replace(
            "\nsteam_app_id = ",
            "\nfrom utils.platform_info import IS_LINUX\n\nsteam_app_id = ",
            1,
        )

    return content


def add_force_windows_to_install(content):
    """Add force_windows=IS_LINUX to the steamcmd.download() call in install()."""
    # Pattern: validate=False,\n    ) — at the end of install()'s download call
    if "force_windows=IS_LINUX" not in content:
        content = content.replace(
            "        validate=False,\n    )\n",
            "        validate=False,\n        force_windows=IS_LINUX,\n    )\n",
            1,
        )
    return content


def add_force_windows_to_update(content):
    """Add force_windows=IS_LINUX to the steamcmd.download() call in update()."""
    # Pattern used in most modules: single-line call ending with validate=validate)
    if content.count("force_windows=IS_LINUX") < 2:
        # Try single-line form
        content = content.replace(
            "steam_anonymous_login_possible, validate=validate)",
            "steam_anonymous_login_possible, validate=validate, force_windows=IS_LINUX)",
            1,
        )
        # Try keyword only form (starruptureserver uses validate=validate at end)
        content = content.replace(
            ", validate=validate)\n",
            ", validate=validate, force_windows=IS_LINUX)\n",
            1,
        )
    return content


def extract_list_expr(text, start):
    """Extract a balanced [...] expression starting at position `start`.

    Returns (list_expr, end_pos) or (None, -1) on failure.
    """
    if text[start] != "[":
        return None, -1
    depth = 0
    i = start
    in_str = False
    str_char = None
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\" and i + 1 < len(text):
                i += 2
                continue
            if c == str_char:
                in_str = False
        else:
            if c in ('"', "'"):
                in_str = True
                str_char = c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1], i + 1
        i += 1
    return None, -1


def transform_get_start_command(content, module_name):
    """Transform get_start_command() to remove './' prefix and add proton wrapping.

    Handles the following return patterns found in the modules:
    - return ["./" + server.data["exe_name"], ...], server.data["dir"]
    - return (["./" + server.data["exe_name"], ...], server.data["dir"])
    - Dynamically built 'command' variable returned as (command, dir)
    """
    # Remove all occurrences of '"./" + ' before server.data["exe_name"]
    content = content.replace('"./" + server.data["exe_name"]', 'server.data["exe_name"]')

    # Special handling for askaserver.py which builds 'command' dynamically
    if 'return (command, server.data["dir"])' in content:
        old = '    return (command, server.data["dir"])'
        new = (
            '    if IS_LINUX:\n'
            '        command = proton.wrap_command(\n'
            '            command, wineprefix=server.data.get("wineprefix")\n'
            '        )\n'
            '    return (command, server.data["dir"])'
        )
        if old in content:
            content = content.replace(old, new, 1)
            return content

    # Find every occurrence of `return (` or `return [` that contains
    # server.data["exe_name"] as the first list element and ends with
    # server.data["dir"]. Use a bracket-aware parser.
    RETURN_DIR_SUFFIX = ', server.data["dir"]'

    # Search for 'return ' in get_start_command context
    func_marker = "def get_start_command(server):"
    func_start = content.find(func_marker)
    if func_start == -1:
        print(f"  WARNING: no get_start_command in {module_name}")
        return content

    # Find the next function after get_start_command to limit our search scope
    next_def = content.find("\ndef ", func_start + 1)
    search_end = next_def if next_def != -1 else len(content)

    # Work within the function body
    body = content[func_start:search_end]
    body_offset = func_start

    # Find 'return' that starts with a list or '(' containing a list
    for m in re.finditer(r"    return ", body):
        ret_pos = m.end()  # position right after 'return ' (relative to body)

        # Skip 'return (' patterns — unwrap the outer paren first
        has_outer_paren = body[ret_pos] == "("
        # Position in body after '(' (or directly at '[' for no-paren case)
        inner_pos = ret_pos + 1 if has_outer_paren else ret_pos

        # Skip whitespace/newlines between '(' and '[' (handles multi-line returns)
        while inner_pos < len(body) and body[inner_pos] in (" ", "\n", "\t"):
            inner_pos += 1

        # Must start a list
        if inner_pos >= len(body) or body[inner_pos] != "[":
            continue

        abs_inner = body_offset + inner_pos
        list_expr, list_end_abs = extract_list_expr(content, abs_inner)
        if list_expr is None:
            continue
        if 'server.data["exe_name"]' not in list_expr:
            continue

        # After the list, expect (optional whitespace) ', server.data["dir"]'
        # and optional trailing comma + ')' — handles single-line, multi-line,
        # and trailing-comma variants (e.g. `[...],\n    server.data["dir"],\n)`)
        rest_match = re.match(
            r',?\s*server\.data\["dir"\],?\s*\)?',
            content[list_end_abs:],
        )
        if rest_match is None:
            continue
        stmt_end = list_end_abs + rest_match.end()
        # Consume a trailing newline if present
        if stmt_end < len(content) and content[stmt_end] == "\n":
            stmt_end += 1

        # Found the return statement. Build replacement.
        indent = "    "
        replacement = (
            f"{indent}cmd = {list_expr}\n"
            f"{indent}if IS_LINUX:\n"
            f"{indent}    cmd = proton.wrap_command("
            f'cmd, wineprefix=server.data.get("wineprefix"))\n'
            f"{indent}return cmd, server.data[\"dir\"]\n"
        )

        abs_stmt_start = body_offset + m.start()  # start of '    return '
        content = content[:abs_stmt_start] + replacement + content[stmt_end:]
        return content

    print(f"  WARNING: Could not transform get_start_command in {module_name}.py")
    return content


def transform_file(module_name):
    """Apply all proton-support transformations to a single game module."""
    path = f"src/gamemodules/{module_name}.py"
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  ERROR: {path} not found")
        return False

    original = content

    content = add_imports(content)
    content = add_force_windows_to_install(content)
    content = add_force_windows_to_update(content)
    content = transform_get_start_command(content, module_name)

    if content == original:
        print(f"  SKIP (already transformed or no changes): {module_name}.py")
        return True

    if DRY_RUN:
        print(f"  [DRY-RUN] Would update: {path}")
        # Show first diff-like output
        orig_lines = original.splitlines()
        new_lines = content.splitlines()
        for i, (o, n) in enumerate(zip(orig_lines, new_lines)):
            if o != n:
                print(f"    Line {i+1}: -{o!r}")
                print(f"    Line {i+1}: +{n!r}")
        return True

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {path}")
    return True


def main():
    print(f"Applying Wine/Proton support to {len(MODULES)} game modules...")
    if DRY_RUN:
        print("  (DRY-RUN mode — no files will be written)")
    failed = []
    for module in MODULES:
        ok = transform_file(module)
        if not ok:
            failed.append(module)
    if failed:
        print(f"\nFailed: {failed}")
        sys.exit(1)
    else:
        print(f"\nDone. {len(MODULES)} modules processed.")


if __name__ == "__main__":
    main()
