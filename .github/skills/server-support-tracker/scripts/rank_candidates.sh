#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

SUPPORT_DOC="$REPO_ROOT/docs/game-server-support.md"
PARITY_DOC="$REPO_ROOT/docs/module_parity_report.md"
STATUS_DOC="$REPO_ROOT/docs/TEST_STATUS.md"
DISABLED_CONF="$REPO_ROOT/disabled_servers.conf"
SHOW_ALL=0

if [[ "${1:-}" == "--all" ]]; then
  SHOW_ALL=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: bash .github/skills/server-support-tracker/scripts/rank_candidates.sh [--all]" >&2
  exit 1
fi

python3 - "$SUPPORT_DOC" "$PARITY_DOC" "$STATUS_DOC" "$DISABLED_CONF" "$SHOW_ALL" <<'PY'
import csv
import re
import sys
from pathlib import Path

support_doc = Path(sys.argv[1])
parity_doc = Path(sys.argv[2])
status_doc = Path(sys.argv[3])
disabled_conf = Path(sys.argv[4])
show_all = sys.argv[5] == "1"


def parse_support(path: Path):
    supported = set()
    unsupported = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [x] "):
            supported.add(line[len("- [x] ") :].strip())
        elif line.startswith("- [ ] "):
            unsupported.add(line[len("- [ ] ") :].strip())
    return supported, unsupported


def parse_parity_active(path: Path):
    active = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 5:
            continue
        canonical_id = parts[1]
        state = parts[3]
        if canonical_id and canonical_id != "canonical_id" and state == "active":
            active.add(canonical_id)
    return active


def parse_status(path: Path):
    status = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 3:
            continue
        module = parts[1]
        reason = parts[2]
        if module and module != "module":
            status[module] = reason
    return status


def parse_disabled(path: Path):
    disabled = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t", 1)
        module = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else "No reason given"
        disabled[module] = reason
    return disabled


def classify(module: str, reason: str, active_unchecked: set[str], unsupported_not_disabled: set[str], disabled_non_auth: set[str]):
    score = 0
    lane = ""
    lowered = reason.lower()

    if module in active_unchecked:
        score += 100
        lane = "active-but-unchecked"
    elif module in unsupported_not_disabled:
        score += 70
        lane = "unsupported-not-disabled"
    elif module in disabled_non_auth:
        score += 35
        lane = "disabled-non-auth"
    else:
        lane = "other"

    if "passed" in lowered:
        score += 40
    if "prerequisite" in lowered:
        score += 30
    if "dotnet" in lowered or "pak0" in lowered:
        score += 25
    if "download prerequisite" in lowered:
        score += 20
    if "404" in lowered or "dead" in lowered or "403 forbidden" in lowered:
        score -= 20
    if "timeout" in lowered or "too large" in lowered:
        score -= 15
    if any(token in lowered for token in ("segfault", "crash", "crashes", "exits immediately", "never creates", "never completes", "stalls", "connection refused")):
        score -= 30
    if "authentication" in lowered:
        score -= 1000

    return score, lane


supported, unsupported = parse_support(support_doc)
active = parse_parity_active(parity_doc)
status_map = parse_status(status_doc)
disabled_map = parse_disabled(disabled_conf)

active_unchecked = active & unsupported
unsupported_not_disabled = unsupported - set(disabled_map)
disabled_non_auth = {module for module, reason in disabled_map.items() if "requires authentication" not in reason.lower()}

candidates = {}
for module in sorted(active_unchecked | unsupported_not_disabled | disabled_non_auth):
    reason = status_map.get(module, disabled_map.get(module, "No status note recorded"))
    score, lane = classify(module, reason, active_unchecked, unsupported_not_disabled, disabled_non_auth)
    if score <= -900:
        continue
    candidates[module] = {"score": score, "lane": lane, "reason": reason}

rows = sorted(candidates.items(), key=lambda item: (-item[1]["score"], item[0]))
limit = len(rows) if show_all else 25

print("Ranked non-auth AlphaGSM candidates")
print(f"Total ranked candidates: {len(rows)}")
print()
writer = csv.writer(sys.stdout)
writer.writerow(["score", "lane", "module", "reason"])
for module, payload in rows[:limit]:
    writer.writerow([payload["score"], payload["lane"], module, payload["reason"]])
if not show_all and len(rows) > limit:
    print(f"... {len(rows) - limit} more (rerun with --all)")
PY