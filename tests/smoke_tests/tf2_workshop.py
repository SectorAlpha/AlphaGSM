"""TF2 native Workshop readiness and current-map attribution from a fresh console frame."""

import argparse
from pathlib import Path
import re


_ANSI_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def _console_lines(text):
    """Return stripped console lines with ANSI color codes removed."""
    text = _ANSI_RE.sub('', text)
    return [line.strip() for line in text.splitlines()]


def probe_began(text, token):
    """Return whether this probe's own BEGIN delimiter is in the console text."""
    return f'BEGIN-{token}' in _console_lines(text)


def _native_frame(text, item_id, map_name, token):
    """Read the latest complete, explicitly delimited engine response."""
    assert re.fullmatch(r'[1-9][0-9]*', str(item_id)), 'Invalid Workshop item ID'
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', map_name), 'Invalid Workshop map name'
    lines = _console_lines(text)
    starts = [index for index, line in enumerate(lines) if line == f'BEGIN-{token}']
    assert starts, 'No fresh TF2 native Workshop probe began'
    end = next((index for index in range(starts[-1] + 1, len(lines))
                if lines[index] == f'END-{token}'), None)
    assert end is not None, 'TF2 native Workshop probe did not finish'
    frame = lines[starts[-1] + 1:end]
    return frame


def assert_native_ready(text, item_id, map_name, token):
    """Require the native downloader's exact item-to-map ready mapping."""
    frame = _native_frame(text, item_id, map_name, token)
    canonical = f'workshop/{map_name}.ugc{item_id}'
    assert any(re.fullmatch(rf'{re.escape(str(item_id))}\s+{re.escape(canonical)}\s+ready', line)
               for line in frame), f'TF2 did not report native item {item_id} ready as {canonical}'
    return canonical


def assert_native_map(text, item_id, map_name, token):
    """Require Valve's exact ready mapping and the engine's current canonical map."""
    canonical = assert_native_ready(text, item_id, map_name, token)
    frame = _native_frame(text, item_id, map_name, token)
    assert any(re.match(rf'map\s*:\s*{re.escape(canonical)}\s+at:', line)
               for line in frame), f'TF2 is not executing native map {canonical}'
    return canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log_path', type=Path)
    parser.add_argument('item_id')
    parser.add_argument('map_name')
    parser.add_argument('token')
    parser.add_argument('--ready-only', action='store_true',
                        help='Check native download readiness before requesting changelevel')
    args = parser.parse_args()
    check = assert_native_ready if args.ready_only else assert_native_map
    canonical = check(args.log_path.read_text(errors='replace'), args.item_id,
                      args.map_name, args.token)
    print(f'Native Workshop map {canonical}: ' + ('ready' if args.ready_only else 'executing'))


if __name__ == '__main__':
    main()
