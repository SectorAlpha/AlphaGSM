#!/usr/bin/env bash

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-1800}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itenshrouded}"
SERVER_STARTED=0
LOCAL_DOCKER_IMAGE="${LOCAL_DOCKER_IMAGE:-alphagsm-wine-proton-runtime:local}"
PUBLISHED_DOCKER_IMAGE="${PUBLISHED_DOCKER_IMAGE:-ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

resolve_docker_image() {
  if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-}" ]]; then
    printf '%s\n' "$ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON"
    return 0
  fi

  if docker image inspect "$LOCAL_DOCKER_IMAGE" >/dev/null 2>&1; then
    printf '%s\n' "$LOCAL_DOCKER_IMAGE"
    return 0
  fi

  printf '%s\n' "$PUBLISHED_DOCKER_IMAGE"
}

run_alphagsm() {
  echo
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
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

DOCKER_IMAGE="$(resolve_docker_image)"
WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" enshrouded-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/enshrouded-server"
CONFIG_PATH="$WORK_DIR/alphagsm-enshrouded.conf"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port)"
QUERYPORT="$(pick_free_port)"
while [[ "$QUERYPORT" == "$PORT" ]]; do
  QUERYPORT="$(pick_free_port)"
done

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
sessiontag = AlphaGSM-enshrouded-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using query port: $QUERYPORT"

run_create_or_skip_disabled "$SERVER_NAME" create enshrouded
run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"
run_alphagsm "$SERVER_NAME" set queryport "$QUERYPORT"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

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
