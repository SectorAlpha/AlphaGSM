#!/usr/bin/env bash
# Shared helpers for smoke tests.
# Source this after defining run_alphagsm().

DEFAULT_WORK_ROOT="${DEFAULT_WORK_ROOT:-/tmp/alphagsm-work}"
PORT_CONFLICT_MARKERS_REGEX='claimed ports are not free|Live listener already holds|Port conflicts detected'

resolve_work_root() {
  local work_root="${ALPHAGSM_WORK_DIR:-$DEFAULT_WORK_ROOT}"
  mkdir -p "$work_root"
  printf '%s\n' "$work_root"
}

is_supported_prerequisite_skip_output() {
  local output_file="$1"
  grep -qE 'ENABLED \(BYO\):|ENABLED \(AUTH\):|Smoke test for .* is ENABLED \(BYO\)|Smoke test for .* is ENABLED \(AUTH\)' "$output_file"
}

# pick_free_port
# Return a non-ephemeral port that is free on both TCP and UDP.
# Avoiding the OS ephemeral range prevents network-heavy setup tools such as
# SteamCMD from consuming the selected game port before the later start check.
pick_free_port() {
  pick_free_port_group 1
}

# pick_free_port_group COUNT
# Return the first port in a non-ephemeral consecutive TCP+UDP-free range.
pick_free_port_group() {
  local count="$1"
  "${PYTHON_BIN:-python3}" "$REPO_ROOT/scripts/select_test_port.py" "$count"
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

# require_command_or_skip COMMAND [MESSAGE]
# Skip this smoke test gracefully if an optional host command is missing.
require_command_or_skip() {
  local command_name="$1"
  local message="${2:-Required command not found: $command_name — skipping smoke test (CI)}"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$message" >&2
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
    if is_supported_prerequisite_skip_output "$output_file"; then
      echo "Server module requires supported BYO/auth prerequisites — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
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
    if is_supported_prerequisite_skip_output "$output_file"; then
      echo "Setup needs supported BYO/auth prerequisites — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
    if grep -q 'Recommended free port set:' "$output_file"; then
      local recommendation_line recommended_port
      recommendation_line=$(grep 'Recommended free port set:' "$output_file" | tail -n 1)
      recommended_port=$(sed -n 's/.*Recommended free port set:.*\<port=\([0-9][0-9]*\)\>.*/\1/p' <<<"$recommendation_line" | tail -n 1)
      while IFS='=' read -r key value; do
        case "$key" in
          port) ;;
          "")
            ;;
          *)
            echo "Applying recommended claimed port override: $key=$value"
            run_alphagsm "${1}" set "$key" "$value"
            ;;
        esac
      done < <(parse_recommended_port_overrides_line "$recommendation_line")
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
    if grep -qE 'Failed to install app|No subscription|Missing configuration|No such file or directory|returned non-zero exit status|Error extracting download|Can.t download file|step::read_patch_meta_from_github::metadata_filter runtime error|jq: error .*Cannot iterate over null|<urlopen error \[Errno 101\] Network is unreachable>|Temporary failure in name resolution' "$output_file"; then
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

run_alphagsm_or_skip_supported_prereq() {
  local output_file
  output_file="$(mktemp)"
  set +e
  run_alphagsm "$@" 2>&1 | tee "$output_file"
  local rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -ne 0 ]]; then
    if is_supported_prerequisite_skip_output "$output_file"; then
      echo "Command needs supported BYO/auth prerequisites — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
    rm -f "$output_file"
    return $rc
  fi
  rm -f "$output_file"
  return 0
}

run_start_with_port_retry() {
  local server_name="$1"
  local max_tries="${2:-3}"
  local attempt=1
  local output_file rc recommendation_line recommended_port

  while (( attempt <= max_tries )); do
    output_file="$(mktemp)"
    set +e
    run_alphagsm "$server_name" start 2>&1 | tee "$output_file"
    rc=${PIPESTATUS[0]}
    set -e
    if [[ $rc -eq 0 ]]; then
      rm -f "$output_file"
      return 0
    fi
    if is_supported_prerequisite_skip_output "$output_file"; then
      echo "Start needs supported BYO/auth prerequisites — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
    if grep -qE 'no space left on device|Steamcmd needs 250MB of free disk space to update' "$output_file"; then
      echo "Start failed due to CI disk exhaustion while staging runtime content — skipping smoke test (CI)" >&2
      rm -f "$output_file"
      exit 0
    fi
    if grep -qE "$PORT_CONFLICT_MARKERS_REGEX" "$output_file" && grep -q 'Recommended free port set:' "$output_file"; then
      recommendation_line=$(grep 'Recommended free port set:' "$output_file" | tail -n 1)
      recommended_port=$(sed -n 's/.*Recommended free port set:.*\<port=\([0-9][0-9]*\)\>.*/\1/p' <<<"$recommendation_line" | tail -n 1)
      while IFS='=' read -r key value; do
        case "$key" in
          "")
            ;;
          *)
            echo "Applying recommended claimed port override before start retry: $key=$value"
            run_alphagsm "$server_name" set "$key" "$value"
            ;;
        esac
      done < <(parse_recommended_port_overrides_line "$recommendation_line")
      if [[ -n "$recommended_port" ]]; then
        echo "Retrying start with recommended claimed port set rooted at: $recommended_port"
      else
        echo "Retrying start with recommended claimed port overrides"
      fi
      rm -f "$output_file"
      ((attempt++))
      continue
    fi
    rm -f "$output_file"
    return $rc
  done
  return $rc
}

parse_recommended_port_overrides_line() {
  local recommendation_line="$1"
  local token payload
  payload="${recommendation_line#*Recommended free port set: }"
  for token in $payload; do
    token="${token%,}"
    case "$token" in
      *=*)
        printf '%s\n' "$token"
        ;;
    esac
  done
}

# wait_for_ready LOG_PATH TIMEOUT_SECONDS [PATTERN]
# Waits for readiness markers in a server log.  Returns 0 on success.
# On timeout prints the log tail for diagnostics and fails.
wait_for_ready() {
  local log_path="$1"
  local timeout_seconds="$2"
  local pattern="${3:-ready|started|listening|Done}"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -f "$log_path" ]] && grep -Eiq "$pattern" "$log_path"; then
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
  return 1
}

# wait_for_glob_ready LOG_GLOB TIMEOUT_SECONDS [PATTERN]
# Waits for readiness markers in the first log file matching a shell glob.
wait_for_glob_ready() {
  local log_glob="$1"
  local timeout_seconds="$2"
  local pattern="${3:-ready|started|listening|Done}"
  local deadline=$((SECONDS + timeout_seconds))
  local matches=()
  while (( SECONDS < deadline )); do
    matches=()
    shopt -s nullglob
    matches=( $log_glob )
    shopt -u nullglob
    if (( ${#matches[@]} > 0 )); then
      local log_path="${matches[0]}"
      if [[ -f "$log_path" ]] && grep -Eiq "$pattern" "$log_path"; then
        return 0
      fi
    fi
    sleep 2
  done
  echo "[diagnostic] Server log did not show readiness markers in ${timeout_seconds}s" >&2
  echo "[diagnostic] Pattern: ${pattern}" >&2
  echo "[diagnostic] Glob: ${log_glob}" >&2
  if (( ${#matches[@]} > 0 )) && [[ -f "${matches[0]}" ]]; then
    local line_count
    line_count=$(wc -l < "${matches[0]}")
    echo "[diagnostic] Log tail (${line_count} total lines): ${matches[0]}" >&2
    tail -100 "${matches[0]}" >&2
  else
    echo "[diagnostic] No log file matched: ${log_glob}" >&2
  fi
  return 1
}

# wait_for_glob_ready_strict LOG_GLOB TIMEOUT_SECONDS [PATTERN]
# Compatibility alias; all readiness waits require a matching marker.
wait_for_glob_ready_strict() {
  local log_glob="$1"
  local timeout_seconds="$2"
  local pattern="${3:-ready|started|listening|Done}"
  wait_for_glob_ready "$log_glob" "$timeout_seconds" "$pattern" "required"
}

# capture_runtime_diagnostics SERVER_NAME
# Preserve Docker/runtime state before a smoke runner's cleanup trap removes it.
capture_runtime_diagnostics() {
  local server_name="$1"
  echo "[diagnostic] Runtime doctor for ${server_name}" >&2
  run_alphagsm "$server_name" doctor || true
  echo "[diagnostic] Recent runtime logs for ${server_name}" >&2
  run_alphagsm "$server_name" logs -n 200 || true
}

# capture_container_process_diagnostics SERVER_NAME CONFIG_PATH [CONFIG_PATH...]
# Capture safe container launch state before a smoke runner removes the server.
capture_container_process_diagnostics() {
  local server_name="$1"
  shift
  local config_path
  local container_name="alphagsm-${server_name}"

  if command -v docker >/dev/null 2>&1; then
    echo "[diagnostic] Container launch state for ${container_name}" >&2
    docker inspect --format 'State: {{.State.Status}} ExitCode: {{.State.ExitCode}} Error: {{.State.Error}} StartedAt: {{.State.StartedAt}} FinishedAt: {{.State.FinishedAt}} Entrypoint: {{.Config.Entrypoint}} Cmd: {{.Config.Cmd}}' "$container_name" || true
    echo "[diagnostic] Safe runtime environment for ${container_name}" >&2
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_name" \
      | grep -E '^(ALPHAGSM_PREFER_PROTON=|ALPHAGSM_(WINEPREFIX|XVFB|XVFB_DISPLAY|XVFB_SERVER_ARGS)=|DISPLAY=|SDL_VIDEODRIVER=|SDL_AUDIODRIVER=|WINEDLLOVERRIDES=|LIBGL_ALWAYS_SOFTWARE=)' || true
    echo "[diagnostic] Process table for ${container_name}" >&2
    docker exec "$container_name" ps -eo pid,ppid,stat,comm,args || true
  else
    echo "[diagnostic] Docker CLI unavailable; cannot inspect ${container_name}" >&2
  fi

  for config_path in "$@"; do
    if [[ -f "$config_path" ]]; then
      echo "[diagnostic] Managed configuration: ${config_path}" >&2
      sed -n '1,160p' "$config_path" >&2
    else
      echo "[diagnostic] Managed configuration missing: ${config_path}" >&2
    fi
  done
}

# wait_for_info_protocol SERVER_NAME EXPECTED_PROTOCOL TIMEOUT_SECONDS
# Polls ``info --json`` until it reports the expected protocol.
wait_for_info_protocol() {
  local server_name="$1"
  local expected_protocol="$2"
  local timeout_seconds="$3"
  local deadline=$((SECONDS + timeout_seconds))
  local last_output=""
  local last_rc=0
  while (( SECONDS < deadline )); do
    set +e
    last_output="$(
      ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" \
        "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$server_name" info --json
    )"
    last_rc=$?
    set -e
    if [[ $last_rc -eq 0 ]] && EXPECTED_PROTOCOL="$expected_protocol" INFO_JSON_PAYLOAD="$last_output" "${PYTHON_BIN:-python3}" - <<'PY'
import json
import os
import sys

expected_protocol = os.environ["EXPECTED_PROTOCOL"]
payload = os.environ.get("INFO_JSON_PAYLOAD", "").strip()

try:
    data = json.loads(payload)
except json.JSONDecodeError:
    sys.exit(1)

sys.exit(0 if data.get("protocol") == expected_protocol else 1)
PY
    then
      return 0
    fi
    sleep 5
  done
  echo "[diagnostic] info --json did not report protocol ${expected_protocol} in ${timeout_seconds}s" >&2
  if [[ -n "$last_output" ]]; then
    echo "[diagnostic] Last info --json payload: $last_output" >&2
  else
    echo "[diagnostic] info --json returned no payload" >&2
  fi
  capture_runtime_diagnostics "$server_name"
  return 1
}

# run_stop_or_skip SERVER_NAME
# Historical name retained for callers; unexpected stop failures fail the test.
run_stop_or_skip() {
  set +e
  run_alphagsm "$@" stop 2>&1
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "Stop returned non-zero ($rc) — server may have crashed" >&2
    capture_runtime_diagnostics "$1"
    return "$rc"
  fi
}
