#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itseserver}"
SERVER_STARTED=0
WORKSHOP_CONFIGURED=0
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-docker}"
if [[ "$RUNTIME_BACKEND" == auto ]]; then RUNTIME_BACKEND=docker; fi
LOCAL_WINE_PROTON_IMAGE="${LOCAL_WINE_PROTON_IMAGE:-alphagsm-wine-proton-runtime:local}"
PUBLISHED_WINE_PROTON_IMAGE="${PUBLISHED_WINE_PROTON_IMAGE:-ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest}"

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
  if docker image inspect "$LOCAL_WINE_PROTON_IMAGE" >/dev/null 2>&1; then
    echo "$LOCAL_WINE_PROTON_IMAGE"
    return
  fi
  echo "$PUBLISHED_WINE_PROTON_IMAGE"
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
    capture_application_logs "$INSTALL_DIR"/*.log "$INSTALL_DIR"/Logs/*.log
    capture_runtime_diagnostics "$SERVER_NAME"
  fi
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    if run_alphagsm "$SERVER_NAME" stop && [[ "$WORKSHOP_CONFIGURED" == 1 ]]; then
      run_alphagsm "$SERVER_NAME" mod cleanup
    fi
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
case "$RUNTIME_BACKEND" in
  docker) require_cmd docker ;;
  process) require_cmd wine; require_cmd xvfb-run ;;
  *) echo "ALPHAGSM_TEST_RUNTIME_BACKEND must be process, docker, or auto" >&2; exit 1 ;;
esac

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" seserver-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/seserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-seserver.conf"
IMAGE=""
if [[ "$RUNTIME_BACKEND" == docker ]]; then IMAGE="$(resolve_runtime_image)"; fi

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
backend = $RUNTIME_BACKEND

[process]
backend = subprocess

[docker]
image_wine_proton = $IMAGE
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using image: $IMAGE"

run_create_or_skip_disabled "$SERVER_NAME" create seserver
run_alphagsm "$SERVER_NAME" set wineprefix "$INSTALL_DIR/.alphagsm-wineprefix"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == 1 ]]; then
  WORKSHOP_CONFIGURED=1
  run_alphagsm "$SERVER_NAME" mod add workshop 1521905890
  run_alphagsm "$SERVER_NAME" mod apply
fi
for previous_log in "$INSTALL_DIR"/SpaceEngineersDedicated_*.log; do
  [[ ! -L "$previous_log" ]]
  rm -f -- "$previous_log"
done
SERVER_STARTED=1
run_start_with_port_retry "$SERVER_NAME"
wait_for_glob_ready_strict "$INSTALL_DIR/SpaceEngineersDedicated_*.log" "$START_TIMEOUT_SECONDS" "Game ready"
if [[ "$WORKSHOP_CONFIGURED" == 1 ]]; then
  "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/seserver_workshop.py" "$INSTALL_DIR"
fi
wait_for_info_protocol "$SERVER_NAME" "udp" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
if ! run_alphagsm "$SERVER_NAME" info; then
  wait_for_info_protocol "$SERVER_NAME" "udp" 120
  run_alphagsm "$SERVER_NAME" info
fi
if ! run_alphagsm "$SERVER_NAME" info --json; then
  wait_for_info_protocol "$SERVER_NAME" "udp" 120
  run_alphagsm "$SERVER_NAME" info --json
fi
run_alphagsm "$SERVER_NAME" stop
SERVER_STARTED=0
if [[ "$WORKSHOP_CONFIGURED" == 1 ]]; then
  run_alphagsm "$SERVER_NAME" mod cleanup
  WORKSHOP_CONFIGURED=0
fi
run_alphagsm "$SERVER_NAME" status
