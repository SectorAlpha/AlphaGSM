"""TF2 native Workshop readiness and current-map attribution from a fresh console frame."""

import argparse
from pathlib import Path
import re


def assert_native_map(text, item_id, map_name, token):
    """Require Valve's exact ready mapping and the engine's current canonical map."""
    assert re.fullmatch(r'[1-9][0-9]*', str(item_id)), 'Invalid Workshop item ID'
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', map_name), 'Invalid Workshop map name'
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    lines = [line.strip() for line in text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == f'BEGIN-{token}']
    assert starts, 'No fresh TF2 native Workshop probe began'
    end = next((index for index in range(starts[-1] + 1, len(lines))
                if lines[index] == f'END-{token}'), None)
    assert end is not None, 'TF2 native Workshop probe did not finish'
    frame = lines[starts[-1] + 1:end]
    canonical = f'workshop/{map_name}.ugc{item_id}'
    assert any(re.fullmatch(rf'{re.escape(str(item_id))}\s+{re.escape(canonical)}\s+ready', line)
               for line in frame), f'TF2 did not report native item {item_id} ready as {canonical}'
    assert any(re.match(rf'map\s*:\s*{re.escape(canonical)}\s+at:', line)
               for line in frame), f'TF2 is not executing native map {canonical}'
    return canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log_path', type=Path)
    parser.add_argument('item_id')
    parser.add_argument('map_name')
    parser.add_argument('token')
    args = parser.parse_args()
    canonical = assert_native_map(args.log_path.read_text(errors='replace'), args.item_id,
                                  args.map_name, args.token)
    print(f'Engine executes native Workshop map {canonical}')


if __name__ == '__main__':
    main()
