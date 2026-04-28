#!/usr/bin/env python3
"""List gamemodule files missing runtime/container hooks.

Scans `src/gamemodules` for Python modules and reports files that do not
define `get_runtime_requirements` or `get_container_spec` at top-level.
"""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
GM_PATH = os.path.join(ROOT, "src", "gamemodules")

hook_re = re.compile(r"\bget_runtime_requirements\b|\bget_container_spec\b")

def scan():
    missing = []
    for dirpath, dirs, files in os.walk(GM_PATH):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding='utf-8').read()
            except Exception:
                continue
            has_runtime = 'get_runtime_requirements' in text
            has_container = 'get_container_spec' in text
            if not (has_runtime and has_container):
                missing.append({'path': rel.replace('\\', '/'), 'has_runtime': has_runtime, 'has_container': has_container})
    return missing

def main():
    miss = scan()
    print('Found %d modules missing hooks (either runtime or container).' % (len(miss),))
    for m in sorted(miss, key=lambda x: x['path']):
        flags = []
        if not m['has_runtime']:
            flags.append('runtime_requirements')
        if not m['has_container']:
            flags.append('container_spec')
        print('%s - missing: %s' % (m['path'], ', '.join(flags)))

if __name__ == '__main__':
    main()
