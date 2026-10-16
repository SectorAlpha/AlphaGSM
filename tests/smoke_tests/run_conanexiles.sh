#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-900}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itconanexiles}"
SERVER_STARTED=0
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-docker}"
LOCAL_STEAMCMD_LINUX_IMAGE="${LOCAL_STEAMCMD_LINUX_IMAGE:-alphagsm-steamcmd-linux-runtime:local}"
PUBLISHED_STEAMCMD_LINUX_IMAGE="${PUBLISHED_STEAMCMD_LINUX_IMAGE:-ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

resolve_runtime_image() {
  if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX:-}" ]]; then
    echo "$ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX"
    return
  fi
  if docker image inspect "$LOCAL_STEAMCMD_LINUX_IMAGE" >/dev/null 2>&1; then
    echo "$LOCAL_STEAMCMD_LINUX_IMAGE"
    return
  fi
  echo "$PUBLISHED_STEAMCMD_LINUX_IMAGE"
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
    capture_application_logs "$INSTALL_DIR"/ConanSandbox/Saved/Logs/*.log
    capture_runtime_diagnostics "$SERVER_NAME"
  fi
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
    if [[ "$?" -eq 0 ]]; then
      run_alphagsm "$SERVER_NAME" mod cleanup
    fi
  fi
  return "$rc"
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
if [[ "$RUNTIME_BACKEND" == "docker" ]]; then
  require_cmd docker
fi

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" conanexiles-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="${ALPHAGSM_CONAN_INSTALL_DIR:-$WORK_DIR/conanexiles-server}"
CONFIG_PATH="$WORK_DIR/alphagsm-conanexiles.conf"
IMAGE="$(resolve_runtime_image)"

mkdir -p "$HOME_DIR"
PORT="$(pick_free_port_group 2)"
QUERY_PORT="$(pick_free_port)"
while [[ "$QUERY_PORT" -eq "$PORT" || "$QUERY_PORT" -eq "$((PORT + 1))" ]]; do
  QUERY_PORT="$(pick_free_port)"
done

cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR

[downloader]
db_path = $HOME_DIR/downloads/downloads.txt
target_path = $HOME_DIR/downloads/downloads

[downloader.steamcmd]
steamcmd_path = $WORK_ROOT/steamcmd

[server]
datapath = $HOME_DIR/conf

[runtime]
backend = $RUNTIME_BACKEND

[process]
backend = subprocess
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using query port: $QUERY_PORT"
echo "Using image: $IMAGE"

run_create_or_skip_disabled "$SERVER_NAME" create conanexiles
run_alphagsm "$SERVER_NAME" set image "$IMAGE"
run_alphagsm "$SERVER_NAME" set queryport "$QUERY_PORT"
run_alphagsm "$SERVER_NAME" set servername "AlphaGSM Conan Smoke"
run_alphagsm "$SERVER_NAME" set maxplayers 16
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
run_alphagsm "$SERVER_NAME" mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=3733835102
run_alphagsm "$SERVER_NAME" mod apply
if [[ -d "$INSTALL_DIR/ConanSandbox/Saved/Logs" ]]; then
  for _old_log in "$INSTALL_DIR"/ConanSandbox/Saved/Logs/*.log; do
    if [[ -f "$_old_log" ]]; then
      mv "$_old_log" "${_old_log%.log}.previous"
    fi
  done
fi
run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
"$PYTHON_BIN" - "$INSTALL_DIR" <<'PY'
from pathlib import Path
import re
import sys
logs = Path(sys.argv[1]) / "ConanSandbox/Saved/Logs"
pattern = r"LogModManager:.*Mounting mod pak file:.*3733835102[/\\]StorageReachExpanded\.pak"
assert any(re.search(pattern, text) and "[StorageReachExpanded] Active!" in text
           for text in (path.read_text(errors="replace") for path in logs.glob("*.log"))), \
    "The fresh native engine log did not prove Workshop PAK mounting"
PY
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" mod cleanup
run_alphagsm "$SERVER_NAME" status
