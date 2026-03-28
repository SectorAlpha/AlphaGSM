#!/usr/bin/env python3
"""Fix unit test module files for newly-protonized Windows-only game servers.

Usage: python3 scripts/fix_proton_module_tests.py [--dry-run]

Two tasks:
  1. Revert incorrectly-modified cov files (pcars2server matches rs2server substring)
  2. Fix *_modules.py / *_module.py test files:
     - Add monkeypatch + proton.wrap_command mock to get_start_command tests
     - Fix "./exe" → "exe" assertions (since "./" prefix was removed from modules)
     - Ensure steamcmd.download lambdas accept force_windows=False
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# The 42 modules we added proton support to
PROTON_MODULES = {
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
}


def revert_cov_file(path: Path) -> None:
    """Remove incorrect IS_LINUX/proton additions from a cov file that belongs
    to a module that does NOT use proton (e.g. pcars2server tripped a substring
    match on 'rs2server')."""
    content = path.read_text(encoding="utf-8")
    original = content

    # Revert the proton_mock setup we wrongly inserted
    proton_mock_setup = (
        "_proton_mock = MagicMock()\n"
        "_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None: list(cmd)\n"
    )
    content = content.replace(proton_mock_setup, "", 1)

    # Revert the patch.dict change
    content = content.replace(
        "'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock})",
        "'utils.steamcmd': MagicMock()})",
        1,
    )

    # Revert the test_get_start_command signature change
    old_sig = (
        "def test_get_start_command(tmp_path, monkeypatch):\n"
        "    monkeypatch.setattr(mod, \"IS_LINUX\", False)\n"
    )
    content = content.replace(old_sig, "def test_get_start_command(tmp_path):\n", 1)

    if content == original:
        print(f"  SKIP (not modified): {path.name}")
        return

    if DRY_RUN:
        print(f"  [DRY-RUN] Would revert: {path.name}")
        return

    path.write_text(content, encoding="utf-8")
    print(f"  Reverted: {path.name}")


def get_windows_modules_imported(content: str) -> list:
    """Return the exact Windows module names imported via 'import gamemodules.X as X'."""
    found = []
    for mod in PROTON_MODULES:
        pattern = rf'import gamemodules\.{re.escape(mod)} as {re.escape(mod)}'
        if re.search(pattern, content):
            found.append(mod)
    return found


def find_function_bounds(content: str, func_start: int) -> tuple:
    """Given the position of 'def func_name(' in content, return (body_start, body_end).

    body_start: position right after the first `:\n`
    body_end: position of the next `def ` at the same or outer indentation, or EOF
    """
    # Find the colon that ends the signature line
    colon_pos = content.find(":\n", func_start)
    if colon_pos == -1:
        return -1, -1
    body_start = colon_pos + 2  # skip :\n

    # Find next def at indentation 0 (i.e., '\ndef ') after body_start
    next_def = content.find("\ndef ", body_start)
    body_end = next_def + 1 if next_def != -1 else len(content)  # +1 to include the \n
    return body_start, body_end


def fix_test_modules_file(path: Path) -> bool:
    """Fix function signatures and assertions for Windows-module get_start_command tests."""
    content = path.read_text(encoding="utf-8")
    original = content

    windows_mods = get_windows_modules_imported(content)
    if not windows_mods:
        return True

    # Fix 1: steamcmd.download lambda — add force_windows=False if missing
    content = content.replace(
        "lambda path, app_id, anon, validate=True: calls.append(",
        "lambda path, app_id, anon, validate=True, force_windows=False: calls.append(",
    )

    # Fix 2: For each Windows module, find get_start_command test functions and patch them
    for mod_name in windows_mods:
        call_str = f"{mod_name}.get_start_command"
        mock_line = (
            f"    monkeypatch.setattr({mod_name}.proton, "
            f'"wrap_command", lambda cmd, wineprefix=None: list(cmd))\n'
        )

        # Find all `def test_*(tmp_path):` functions in the file
        for sig_match in re.finditer(r"def test_[^\(]+\(tmp_path\):\n", content):
            sig_start = sig_match.start()
            sig_end = sig_match.end()

            # Check if this function's body contains the module's get_start_command call
            body_start, body_end = find_function_bounds(content, sig_start)
            if body_start == -1:
                continue
            body = content[body_start:body_end]

            if call_str not in body:
                continue  # Not a function we need to patch

            # Add monkeypatch to signature and insert mock at body start
            old_sig = sig_match.group(0)
            new_sig = (
                old_sig.rstrip("\n").rstrip("):") + ", monkeypatch):\n"
                + mock_line
            )
            content = content.replace(old_sig, new_sig, 1)

            # Now fix "./exe" assertions within the (now-shifted) body
            # Recompute body bounds after the replacement
            new_sig_match = re.search(re.escape(new_sig[:40]), content)
            if new_sig_match:
                new_body_start, new_body_end = find_function_bounds(
                    content, new_sig_match.start()
                )
                if new_body_start != -1:
                    body_section = content[new_body_start:new_body_end]
                    # Remove "./" prefix from first-element assertions
                    patched_body = re.sub(
                        r'(assert cmd\[0\] == )"\./',
                        r'\1"',
                        body_section,
                    )
                    # Remove "./" from full-list assertions like cmd == ["./foo.exe", ...]
                    patched_body = re.sub(
                        r'(assert cmd == \[)"\.\/',
                        r'\1"',
                        patched_body,
                    )
                    if patched_body != body_section:
                        content = content[:new_body_start] + patched_body + content[new_body_end:]

    if content == original:
        print(f"  SKIP (already up to date): {path.name}")
        return True

    if DRY_RUN:
        print(f"  [DRY-RUN] Would update: {path.name}")
        return True

    path.write_text(content, encoding="utf-8")
    print(f"  Fixed: {path.name}")
    return True


def main():
    test_dir = Path("tests/gamemodules")
    if not test_dir.exists():
        print("ERROR: tests/gamemodules/ not found")
        sys.exit(1)

    # 1. Revert incorrectly-modified cov files
    # A cov file is correct only if its MODULE NAME exactly matches a proton module
    # Use the pattern test_{modname}_cov.py (exact match)
    print("=== Step 1: Revert incorrectly-patched cov files ===")
    for cov_path in sorted(test_dir.glob("*_cov.py")):
        # Extract the module name from the filename: test_FOO_cov.py → FOO
        stem = cov_path.stem  # e.g. test_pcars2server_cov
        mod_from_name = stem.removeprefix("test_").removesuffix("_cov")
        if mod_from_name not in PROTON_MODULES:
            # Check if we accidentally modified this file
            cov_content = cov_path.read_text(encoding="utf-8")
            if "'utils.proton': _proton_mock" in cov_content:
                revert_cov_file(cov_path)

    # 2. Fix *_modules.py and *_module.py test files
    print("\n=== Step 2: Fix module test files ===")
    module_test_files = sorted(
        list(test_dir.glob("*_modules.py")) + list(test_dir.glob("*_module.py"))
    )
    for f in module_test_files:
        fix_test_modules_file(f)

    print("\nDone.")


if __name__ == "__main__":
    main()
