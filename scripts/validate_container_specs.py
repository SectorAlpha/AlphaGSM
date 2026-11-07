#!/usr/bin/env python3
"""Static validator for `get_container_spec` implementations.

Checks that modules with a `def get_container_spec` either delegate to a
builder or reference `get_start_command` or return a dict with a `command`
value that looks like a list. Reports candidates for manual review.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
GM_DIR = os.path.join(ROOT, "src", "gamemodules")

def scan_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    results = []
    for idx, line in enumerate(lines):
        if line.lstrip().startswith('def get_container_spec'):
            indent = len(line) - len(line.lstrip())
            body = []
            for j in range(idx+1, len(lines)):
                l = lines[j]
                if l.strip().startswith('def ') and (len(l) - len(l.lstrip())) <= indent:
                    break
                body.append(l)
            body_text = ''.join(body)
            ok = False
            reasons = []
            if 'get_start_command' in body_text:
                ok = True
                reasons.append('references get_start_command')
            if 'make_container_spec_builder' in body_text or 'make_runtime_requirements_builder' in body_text:
                ok = True
                reasons.append('uses builder')
            # look for returned dict with 'command':
            if re.search(r"['\"]command['\"]\s*:\s*\[", body_text):
                ok = True
                reasons.append('returns literal command list')
            # also accept returning a dict with a 'command' key (variable or literal)
            if re.search(r"return\s*\{[\s\S]*?['\"]command['\"]\s*:", body_text):
                ok = True
                reasons.append("returns dict with 'command' key")
            # accept alias delegation to another module's get_container_spec
            if re.search(r"return\s+_?ALIAS_MODULE\.get_container_spec\(|return\s+_?alias_module\.get_container_spec\(|return\s+_?ALIAS_MODULE\.get_container_spec", body_text):
                ok = True
                reasons.append('delegates to alias module get_container_spec')
            results.append((path, idx+1, ok, '; '.join(reasons) or 'no indicators'))
    return results

def main():
    suspects = []
    for root, dirs, files in os.walk(GM_DIR):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(root, fn)
            res = scan_file(path)
            for p, ln, ok, reason in res:
                if not ok:
                    suspects.append((os.path.relpath(p, ROOT), ln, reason))

    print('Modules with get_container_spec needing review:')
    if not suspects:
        print(' - none')
        return
    for rel, ln, reason in sorted(suspects):
        print(f' - {rel}:{ln}  -> {reason}')

if __name__ == '__main__':
    main()
