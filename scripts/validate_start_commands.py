#!/usr/bin/env python3
"""Static validator for gamemodule `get_start_command` implementations.

Usage: python3 scripts/validate_start_commands.py

This script scans `src/gamemodules/` for `def get_start_command` and
performs a conservative static check that the function returns a tuple
containing a command list/variable and a working-directory that references
`server.data["dir"]` or `server.data.get("dir"...)`.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
GM_DIR = os.path.join(ROOT, "src", "gamemodules")

def scan_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    results = []
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("def get_start_command"):
            indent = len(line) - len(line.lstrip())
            # gather function body until next top-level def or EOF
            body = []
            for j in range(idx+1, len(lines)):
                l = lines[j]
                if l.strip().startswith("def ") and (len(l) - len(l.lstrip())) <= indent:
                    break
                body.append(l)

            # find return statements and capture multi-line returns
            ok = False
            reason = "no return found"
            j = 0
            while j < len(body):
                l = body[j]
                m = re.match(r"^(\s*)return\s*(.*)$", l)
                if not m:
                    j += 1
                    continue
                return_indent = len(m.group(1))
                rest = m.group(2).rstrip()
                collected = [rest]
                # if return expression looks like it starts a paren or bracket, collect until balanced
                if rest.endswith("(") or rest.endswith("[") or (rest == "" and j + 1 < len(body) and body[j+1].lstrip().startswith("[")):
                    balance = 0
                    # include the current rest and subsequent lines
                    for k in range(j+1, len(body)):
                        line_k = body[k]
                        collected.append(line_k)
                        balance += line_k.count('(') - line_k.count(')')
                        balance += line_k.count('[') - line_k.count(']')
                        # stop when we've seen some closing tokens and the indentation drops
                        if balance <= 0 and (line_k.strip().endswith(")") or line_k.strip().endswith("]") or line_k.strip().endswith(",")):
                            j = k
                            break
                full_return = "".join(collected)
                # conservative check: return must reference server.data and include a comma separating command and cwd
                if "server.data" in full_return and "," in full_return:
                    ok = True
                    reason = full_return.strip().splitlines()[0].strip()
                    break
                else:
                    reason = full_return.strip().splitlines()[0].strip() if full_return.strip() else m.group(0).strip()
                j += 1

            results.append((path, idx+1, ok, reason))
    return results

def main():
    failures = []
    successes = []
    for root, dirs, files in os.walk(GM_DIR):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(root, fn)
            res = scan_file(path)
            for p, lineno, ok, reason in res:
                rel = os.path.relpath(p, ROOT)
                if ok:
                    successes.append((rel, lineno, reason))
                else:
                    failures.append((rel, lineno, reason))

    print("Validate `get_start_command` summary")
    print("================================")
    print(f"Found {len(successes)+len(failures)} modules with get_start_command()\n")
    if successes:
        print("Valid-looking implementations:")
        for rel, ln, reason in sorted(successes):
            print(f" - {rel}:{ln}  -> {reason}")
        print()
    if failures:
        print("Possibly problematic implementations (manual review required):")
        for rel, ln, reason in sorted(failures):
            print(f" - {rel}:{ln}  -> {reason}")
    else:
        print("No obvious problems detected.")

if __name__ == '__main__':
    main()
