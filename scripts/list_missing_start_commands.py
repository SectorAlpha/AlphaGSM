#!/usr/bin/env python3
"""List gamemodule Python files that do not define `get_start_command`.

Usage: python3 scripts/list_missing_start_commands.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
GM_DIR = os.path.join(ROOT, "src", "gamemodules")

missing = []
all_files = []
for root, dirs, files in os.walk(GM_DIR):
    for fn in files:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(root, fn)
        all_files.append(os.path.relpath(path, ROOT))
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        # consider module providing get_start_command by def or by assignment
        if 'get_start_command' not in text:
            missing.append(os.path.relpath(path, ROOT))

print('Gamemodules scanned:', len(all_files))
print('Modules missing get_start_command():', len(missing))
for m in sorted(missing):
    print(' -', m)
