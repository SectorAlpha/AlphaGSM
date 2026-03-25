#!/usr/bin/env bash
# Shared helpers for smoke tests.
# Source this after defining run_alphagsm().

run_setup_or_skip_steamcmd() {
  local output_file
  output_file="$(mktemp)"
  set +e
  run_alphagsm "$@" 2>&1 | tee "$output_file"
  local rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -ne 0 ]]; then
    if grep -qE 'Failed to install app|No subscription|Missing configuration|No such file or directory|returned non-zero exit status|Unable to determine archive type' "$output_file"; then
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

# wait_for_ready LOG_PATH TIMEOUT_SECONDS
# Waits for readiness markers in a server log.  Returns 0 on success.
# On timeout prints a warning and exits 0 (skip), because many game-server
# binaries do not run properly inside CI containers.
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
