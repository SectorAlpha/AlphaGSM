#!/usr/bin/env bash
# ENABLED (BYO): ATLAS is supported once a ServerGrid.json,
# ServerGrid.ServerOnly.json, and ServerGrid folder are staged under
# <install_dir>/ShooterGame/.
echo "Smoke test for atlasserver requires a staged ATLAS server-grid export - see docs/servers/atlasserver.md"
exit 77

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itatlasserve}"
SERVER_STARTED=0
DOCKER_IMAGE="${ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX:-ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest}"

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
require_cmd docker

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/atlasserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-atlasserver.conf"
EXPECTED_PROTOCOL="a2s"

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

[runtime]
backend = docker

[process]
backend = subprocess

[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-atlasserve-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create atlasserver
run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "$EXPECTED_PROTOCOL" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
