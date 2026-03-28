#!/usr/bin/env python3
"""Update integration tests for Windows-only game servers to use require_proton().

Removes pytest.mark.skip from pytestmark and adds require_proton() call to test body.

Usage: python3 scripts/fix_proton_integration_tests.py [--dry-run]
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

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


def fix_integration_test(path: Path) -> bool:
    """Fix a single integration test file."""
    content = path.read_text(encoding="utf-8")
    original = content

    # Skip if already has require_proton
    if "require_proton" in content:
        print(f"  SKIP (already patched): {path.name}")
        return True

    # 1. Add require_proton to conftest imports
    content = content.replace(
        "    require_command,\n",
        "    require_command,\n    require_proton,\n",
        1,
    )

    # 2. Remove pytest.mark.skip from pytestmark
    # Handle both single-line and multi-line skip marks

    # Multi-line form: pytestmark = [pytest.mark.integration, pytest.mark.skip(\n    reason="..."\n)]
    content = re.sub(
        r'pytestmark = \[pytest\.mark\.integration, pytest\.mark\.skip\([^)]*\)\]\n',
        'pytestmark = [pytest.mark.integration]\n',
        content,
        flags=re.DOTALL,
    )

    # Single-line form: pytestmark = [pytest.mark.integration, pytest.mark.skip(reason="...")]
    content = re.sub(
        r'pytestmark = \[pytest\.mark\.integration, pytest\.mark\.skip\(reason="[^"]*"\)\]',
        'pytestmark = [pytest.mark.integration]',
        content,
    )

    # 3. Add require_proton() inside the test function
    # Pattern: after require_steamcmd_opt_in() or require_command("screen")
    # Strategy: insert require_proton() after the last require_*_opt_in() call at start of test
    content = content.replace(
        "    require_steamcmd_opt_in()\n",
        "    require_steamcmd_opt_in()\n    require_proton()\n",
        1,
    )

    if content == original:
        print(f"  WARN (no changes made): {path.name}")
        return False

    if DRY_RUN:
        print(f"  [DRY-RUN] Would update: {path.name}")
        return True

    path.write_text(content, encoding="utf-8")
    print(f"  Fixed: {path.name}")
    return True


def main():
    test_dir = Path("tests/integration_tests")
    if not test_dir.exists():
        print("ERROR: tests/integration_tests/ not found")
        sys.exit(1)

    print(f"Fixing integration tests for {len(MODULES)} Windows-only modules...")
    ok = 0
    warn = 0
    for module in MODULES:
        path = test_dir / f"test_{module}.py"
        if not path.exists():
            print(f"  MISSING: {path}")
            warn += 1
            continue
        if fix_integration_test(path):
            ok += 1
        else:
            warn += 1

    print(f"\nDone. {ok} processed, {warn} warnings.")


if __name__ == "__main__":
    main()
