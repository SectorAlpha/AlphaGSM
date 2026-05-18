#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

SUPPORT_DOC="$REPO_ROOT/docs/game-server-support.md"
PARITY_DOC="$REPO_ROOT/docs/module_parity_report.md"
STATUS_DOC="$REPO_ROOT/docs/TEST_STATUS.md"
DISABLED_CONF="$REPO_ROOT/disabled_servers.conf"
SHOW_ALL=0
JSON_OUTPUT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      SHOW_ALL=1
      ;;
    --json)
      JSON_OUTPUT=1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: bash .github/skills/server-support-tracker/scripts/support_snapshot.sh [--all] [--json]" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -f "$SUPPORT_DOC" || ! -f "$PARITY_DOC" || ! -f "$STATUS_DOC" || ! -f "$DISABLED_CONF" ]]; then
  echo "Required AlphaGSM tracking files are missing." >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

supported_file="$tmpdir/supported.txt"
unsupported_file="$tmpdir/unsupported.txt"
active_file="$tmpdir/active.txt"
disabled_file="$tmpdir/disabled.txt"
active_unchecked_file="$tmpdir/active_unchecked.txt"
unsupported_not_disabled_file="$tmpdir/unsupported_not_disabled.txt"

grep '^- \[x\]' "$SUPPORT_DOC" | sed -E 's/^- \[x\] ([^[:space:]].*)/\1/' | sort -u > "$supported_file"
grep '^- \[ \]' "$SUPPORT_DOC" | sed -E 's/^- \[ \] ([^[:space:]].*)/\1/' | sort -u > "$unsupported_file"
awk -F'|' 'NF >= 4 {
  id=$2
  state=$4
  gsub(/^[ \t]+|[ \t]+$/, "", id)
  gsub(/^[ \t]+|[ \t]+$/, "", state)
  if (id != "canonical_id" && state == "active") print id
}' "$PARITY_DOC" | sort -u > "$active_file"
awk '/^[^#[:space:]]/ {print $1}' "$DISABLED_CONF" | sort -u > "$disabled_file"

comm -12 "$active_file" "$unsupported_file" > "$active_unchecked_file"
comm -23 "$unsupported_file" "$disabled_file" > "$unsupported_not_disabled_file"

supported_count="$(wc -l < "$supported_file")"
unsupported_count="$(wc -l < "$unsupported_file")"
active_count="$(wc -l < "$active_file")"
disabled_count="$(wc -l < "$disabled_file")"
active_unchecked_count="$(wc -l < "$active_unchecked_file")"
unsupported_not_disabled_count="$(wc -l < "$unsupported_not_disabled_file")"

auth_count="$(grep -Eic 'requires authentication' "$DISABLED_CONF")"
dead_url_count="$(grep -Eic 'dead|404|403 Forbidden|download URL unavailable|discontinued' "$DISABLED_CONF")"
invalid_platform_count="$(grep -Eic 'Invalid platform on Linux' "$DISABLED_CONF")"
missing_linux_count="$(grep -Eic 'installs no Linux-compatible|installs no game files|installs incomplete|lacks required runtime modules|not present' "$DISABLED_CONF")"
timeout_count="$(grep -Eic 'timeout|too large' "$DISABLED_CONF")"
startup_failure_count="$(grep -Eic 'segfault|crash|crashes|exits immediately|never creates|never completes|stalls|fails to initialise|fails to create|Connection refused|self-shuts down' "$DISABLED_CONF")"
prereq_count="$(grep -Eic 'pak0|dotnet|database|maps not available|requires Half-Life 2|Windows-only' "$DISABLED_CONF")"

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  python3 - "$REPO_ROOT" "$supported_file" "$unsupported_file" "$active_file" "$disabled_file" "$active_unchecked_file" "$unsupported_not_disabled_file" <<'PY'
import json
import pathlib
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

repo_root = pathlib.Path(sys.argv[1])
supported_file = pathlib.Path(sys.argv[2])
unsupported_file = pathlib.Path(sys.argv[3])
active_file = pathlib.Path(sys.argv[4])
disabled_file = pathlib.Path(sys.argv[5])
active_unchecked_file = pathlib.Path(sys.argv[6])
unsupported_not_disabled_file = pathlib.Path(sys.argv[7])

disabled_conf = repo_root / "disabled_servers.conf"


def read_lines(path: pathlib.Path):
  return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_disabled_map(path: pathlib.Path):
  result = {}
  for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
      continue
    parts = raw.split("\t", 1)
    module = parts[0].strip()
    reason = parts[1].strip() if len(parts) > 1 else "No reason given"
    result[module] = reason
  return result


disabled_map = read_disabled_map(disabled_conf)
payload = {
  "counts": {
    "supported": len(read_lines(supported_file)),
    "unsupported": len(read_lines(unsupported_file)),
    "active": len(read_lines(active_file)),
    "hard_disabled": len(read_lines(disabled_file)),
    "active_but_unchecked": len(read_lines(active_unchecked_file)),
    "unsupported_but_not_disabled": len(read_lines(unsupported_not_disabled_file)),
  },
  "lists": {
    "supported": read_lines(supported_file),
    "unsupported": read_lines(unsupported_file),
    "active": read_lines(active_file),
    "hard_disabled": read_lines(disabled_file),
    "active_but_unchecked": read_lines(active_unchecked_file),
    "unsupported_but_not_disabled": read_lines(unsupported_not_disabled_file),
  },
  "disabled_reasons": disabled_map,
  "blocker_buckets": {
    "requires_authentication": sum("requires authentication" in reason.lower() for reason in disabled_map.values()),
    "dead_or_missing_download_source": sum(any(token in reason.lower() for token in ("dead", "404", "403 forbidden", "download url unavailable", "discontinued")) for reason in disabled_map.values()),
    "invalid_platform_linux": sum("invalid platform on linux" in reason.lower() for reason in disabled_map.values()),
    "missing_linux_binary_or_incomplete_content": sum(any(token in reason.lower() for token in ("installs no linux-compatible", "installs no game files", "installs incomplete", "lacks required runtime modules", "not present")) for reason in disabled_map.values()),
    "download_timeout_or_too_large": sum(any(token in reason.lower() for token in ("timeout", "too large")) for reason in disabled_map.values()),
    "startup_crash_or_readiness_failure": sum(any(token in reason.lower() for token in ("segfault", "crash", "crashes", "exits immediately", "never creates", "never completes", "stalls", "fails to initialise", "fails to create", "connection refused", "self-shuts down")) for reason in disabled_map.values()),
    "external_prerequisite_or_asset_gate": sum(any(token in reason.lower() for token in ("pak0", "dotnet", "database", "maps not available", "requires half-life 2", "windows-only")) for reason in disabled_map.values()),
  },
}
json.dump(payload, sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
PY
  exit 0
fi

print_section() {
  local title="$1"
  echo
  echo "$title"
}

print_list() {
  local file="$1"
  local limit="$2"
  local count
  count="$(wc -l < "$file")"
  if [[ "$count" -eq 0 ]]; then
    echo "  (none)"
    return
  fi
  if [[ "$SHOW_ALL" -eq 1 || "$count" -le "$limit" ]]; then
    sed 's/^/  - /' "$file"
    return
  fi
  head -n "$limit" "$file" | sed 's/^/  - /'
  echo "  ... $(($count - $limit)) more (rerun with --all)"
}

echo "AlphaGSM support snapshot"
echo "Repo: $REPO_ROOT"

print_section "Counts"
echo "  Supported now: $supported_count"
echo "  Unsupported now: $unsupported_count"
echo "  Active modules: $active_count"
echo "  Hard-disabled modules: $disabled_count"
echo "  Active but unchecked: $active_unchecked_count"
echo "  Unsupported but not disabled: $unsupported_not_disabled_count"

print_section "Active But Unchecked"
print_list "$active_unchecked_file" 20

print_section "Unsupported But Not Disabled"
print_list "$unsupported_not_disabled_file" 25

print_section "Disabled Blocker Buckets"
echo "  Requires authentication: $auth_count"
echo "  Dead or missing download source: $dead_url_count"
echo "  Invalid platform on Linux: $invalid_platform_count"
echo "  No Linux-compatible binary or incomplete content: $missing_linux_count"
echo "  Download timeout or too large: $timeout_count"
echo "  Startup crash or readiness failure: $startup_failure_count"
echo "  External prerequisite or asset gate: $prereq_count"
echo "  Note: blocker categories overlap."

print_section "Suggested Next Lanes"
echo "  1. Current CI failures"
echo "  2. Unsupported but not disabled"
echo "  3. Hard-disabled non-auth modules with stale reasons"
echo "  4. Auth-gated SteamCMD modules"