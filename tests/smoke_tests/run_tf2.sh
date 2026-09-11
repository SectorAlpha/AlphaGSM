#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STATUS_HELPER="$REPO_ROOT/tests/smoke_tests/source_status.py"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-ittf2}"
SERVER_STARTED=0
TF2_CURATED_REGISTRY_PATH="${TF2_CURATED_REGISTRY_PATH:-}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

run_alphagsm() {
  echo
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=tests/smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/tf2-server"
CONFIG_PATH="$WORK_DIR/alphagsm-tf2.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-TF2-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port)"

cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR

[downloader]
db_path = $HOME_DIR/downloads/downloads.txt
target_path = $HOME_DIR/downloads/downloads

[server]
datapath = $HOME_DIR/conf

[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-TF2-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using UDP port: $PORT"

run_alphagsm "$SERVER_NAME" create teamfortress2
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

if [[ ! -f "$INSTALL_DIR/srcds_run_64" ]] && [[ ! -f "$INSTALL_DIR/srcds_run" ]]; then
  echo "Expected TF2 launcher not found in $INSTALL_DIR" >&2
  exit 1
fi
test -f "$INSTALL_DIR/tf/cfg/server.cfg"
# Keep the smoke server awake for real A2S query and info checks.
printf '\nsv_hibernate_when_empty 0\ntf_allow_server_hibernation 0\n' >> "$INSTALL_DIR/tf/cfg/server.cfg"

if [[ -n "$TF2_CURATED_REGISTRY_PATH" ]]; then
  echo "Applying curated TF2 mods from override registry: $TF2_CURATED_REGISTRY_PATH"
  ALPHAGSM_TF2_CURATED_REGISTRY_PATH="$TF2_CURATED_REGISTRY_PATH" run_alphagsm "$SERVER_NAME" mod add curated sourcemod
  ALPHAGSM_TF2_CURATED_REGISTRY_PATH="$TF2_CURATED_REGISTRY_PATH" run_alphagsm "$SERVER_NAME" mod apply
  test -f "$INSTALL_DIR/tf/addons/sourcemod/plugins/base.smx"
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" status
