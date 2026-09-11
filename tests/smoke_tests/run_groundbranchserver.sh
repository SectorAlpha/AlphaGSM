#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-900}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itgroundbran}"
SERVER_STARTED=0
LOCAL_DOCKER_IMAGE="${LOCAL_DOCKER_IMAGE:-alphagsm-wine-proton-runtime:local}"
PUBLISHED_DOCKER_IMAGE="${PUBLISHED_DOCKER_IMAGE:-ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

resolve_runtime_image() {
  if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-}" ]]; then
    echo "$ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON"
    return
  fi
  if docker image inspect "$LOCAL_DOCKER_IMAGE" >/dev/null 2>&1; then
    echo "$LOCAL_DOCKER_IMAGE"
    return
  fi
  echo "$PUBLISHED_DOCKER_IMAGE"
}

run_alphagsm() {
  echo
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  local rc=$?
  set +e
  if [[ "$rc" -ne 0 && -n "${INSTALL_DIR:-}" ]]; then
    capture_application_logs "$INSTALL_DIR"/GroundBranch/Saved/Logs/*.log
    capture_runtime_diagnostics "$SERVER_NAME"
  fi
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd docker

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/groundbranchserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-groundbranchserver.conf"
IMAGE="$(resolve_runtime_image)"

mkdir -p "$HOME_DIR"
PORT="$(pick_free_port_group 2)"
QUERY_PORT="$((PORT + 1))"

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

[docker]
image_wine_proton = $IMAGE
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using image: $IMAGE"

run_create_or_skip_disabled "$SERVER_NAME" create groundbranchserver
run_alphagsm "$SERVER_NAME" set image "$IMAGE"
run_alphagsm "$SERVER_NAME" set queryport "$QUERY_PORT"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "udp" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" status
