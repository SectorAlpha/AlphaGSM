"""Require execution of Census's native server console command."""

from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4


def npc_counts(output):
    """Count exact native NPC lines, including the console's first-line prompt."""
    clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output).replace('\r', '')
    lines = [line.strip().removeprefix(': ').strip() for line in clean.splitlines()]
    return {name: lines.count(name) for name in ('Guide', 'Merchant', 'Nurse')}


def assert_census_loaded(run, timeout=60):
    """Require new native output after sending the mod-owned command."""
    before = npc_counts(run('logs', '-n', '1000'))
    run('send', 'TownProgress ' + uuid4().hex)
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        last = run('logs', '-n', '1000')
        after = npc_counts(last)
        if all(after[name] > before[name] for name in before):
            return
        time.sleep(1)
    raise AssertionError('Census TownProgress did not execute in the running server:\n' + last[-12000:])


def main(server_name):
    """Run the same native probe through AlphaGSM for the smoke runner."""
    script = Path(__file__).resolve().parents[2] / 'alphagsm'
    def run(*args):
        result = subprocess.run([sys.executable, str(script), server_name, *args],
                                check=True, capture_output=True, text=True, timeout=120)
        return result.stdout
    assert_census_loaded(run)
    print('Census TownProgress executed inside the running tModLoader server.')


if __name__ == '__main__':
    main(sys.argv[1])
