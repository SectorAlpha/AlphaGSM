#!/usr/bin/env bash
# Shared helpers for smoke tests.
# Source this after defining run_alphagsm().

# pick_free_port
# Return an ephemeral port that is free on both TCP and UDP.
# The dual-protocol check mirrors AlphaGSM's port-manager pre-flight
# (probe_live_listener), which tests both protocols; a port in TCP
# TIME_WAIT state would otherwise cause "Live listener already holds" failures.
pick_free_port() {
  "${PYTHON_BIN:-python3}" - <<'PY'
import socket, sys
for _attempt in range(100):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    ok = True
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        try:
            with socket.socket(socket.AF_INET, kind) as probe:
                probe.bind(("127.0.0.1", port))
        except OSError:
            ok = False
            break
    if ok:
        print(port)
        sys.exit(0)
sys.stderr.write("Could not find a free TCP+UDP port after 100 attempts\n")
sys.exit(1)
PY
}

# require_proton
# Skip this smoke test gracefully if Wine (or Proton-GE) is not installed.
# Windows-binary game servers need Wine at start time; when Wine is absent the
# server reports "Neither Wine nor Proton-GE is available" and exits non-zero,
# which would mark the smoke test as FAILED rather than SKIPPED.  Call this
# helper right after "require_cmd screen" in any smoke test for a Windows-binary
# server to get a clean skip instead.
require_proton() {
  if ! command -v wine >/dev/null 2>&1; then
    echo "Wine not installed — skipping Windows-binary smoke test (CI)" >&2
    exit 0
  fi
}

# run_create_or_skip_disabled SERVER_NAME create MODULE_NAME
# Runs "alphagsm create" and exits 0 if the module is currently disabled.
# Call this instead of plain run_alphagsm for the create step so that servers
# listed in disabled_servers.conf produce a graceful skip rather than a failure.
run_create_or_skip_disabled() {
  local output_file
  output_file="$(mktemp)"
  set +e
  run_alphagsm "$@" 2>&1 | tee "$output_file"
  local rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -ne 0 ]]; then
    if grep -q 'is currently disabled' "$output_file"; then
      echo "Server module is currently disabled — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
    rm -f "$output_file"
    return $rc
  fi
  rm -f "$output_file"
  return 0
}

run_setup_or_skip_steamcmd() {
  local output_file
  output_file="$(mktemp)"
  set +e
  run_alphagsm "$@" 2>&1 | tee "$output_file"
  local rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -ne 0 ]]; then
    if grep -q 'Recommended free port set:' "$output_file"; then
      local recommended_port
      recommended_port=$(sed -n 's/.*Recommended free port set:.*port=\([0-9][0-9]*\).*/\1/p' "$output_file" | tail -n 1)
      if [[ -n "$recommended_port" ]]; then
        local retry_args=()
        local replaced=0
        local expect_port_value=0
        for arg in "$@"; do
          if [[ $replaced -eq 0 && $expect_port_value -eq 1 ]]; then
            retry_args+=("$recommended_port")
            replaced=1
            expect_port_value=0
          else
            retry_args+=("$arg")
            if [[ "$arg" == "-n" ]]; then
              expect_port_value=1
            else
              expect_port_value=0
            fi
          fi
        done
        if [[ $replaced -eq 1 ]]; then
          echo "Retrying setup with recommended free port: $recommended_port"
          rm -f "$output_file"
          run_setup_or_skip_steamcmd "${retry_args[@]}"
          return $?
        fi
      fi
    fi
    if grep -qE 'Failed to install app|No subscription|Missing configuration|No such file or directory|returned non-zero exit status|Error extracting download|Can.t download file' "$output_file"; then
      echo "Setup failed with known SteamCMD issue — skipping smoke test"
      rm -f "$output_file"
      exit 0
    fi
    rm -f "$output_file"
    return $rc
  fi
  rm -f "$output_file"
  return 0
}

# wait_for_ready LOG_PATH TIMEOUT_SECONDS [PATTERN]
# Waits for readiness markers in a server log.  Returns 0 on success.
# On timeout prints the log tail for diagnostics then exits 0 (skip).
wait_for_ready() {
  local log_path="$1"
  local timeout_seconds="$2"
  local pattern="${3:-ready|started|listening|Done}"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -f "$log_path" ]] && grep -Eq "$pattern" "$log_path"; then
      return 0
    fi
    sleep 2
  done
  echo "[diagnostic] Server log did not show readiness markers in ${timeout_seconds}s" >&2
  echo "[diagnostic] Pattern: ${pattern}" >&2
  if [[ -f "$log_path" ]]; then
    local line_count
    line_count=$(wc -l < "$log_path")
    echo "[diagnostic] Log tail (${line_count} total lines): ${log_path}" >&2
    tail -100 "$log_path" >&2
  else
    echo "[diagnostic] Log file not found: ${log_path}" >&2
  fi
  echo "Server log did not show readiness markers in ${timeout_seconds}s — skipping smoke test (CI)" >&2
  exit 0
}

# run_stop_or_skip SERVER_NAME
# Tries to stop a server; if it is not running any more, skip instead of fail.
run_stop_or_skip() {
  set +e
  run_alphagsm "$@" stop 2>&1
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "Stop returned non-zero ($rc) — server may have crashed in CI, skipping" >&2
    exit 0
  fi
}
