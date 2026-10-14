#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-900}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itwreckfestser}"
SERVER_STARTED=0
WORKSHOP_CONFIGURED=0
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-process}"
if [[ -z "${ALPHAGSM_TEST_RUNTIME_BACKEND:-}" ]] && \
   [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-}" || "${GITHUB_ACTIONS:-}" == true ]]; then
  RUNTIME_BACKEND=docker
fi
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

diagnose_wreckfest() {
  local container=""
  local -a observation_args=("$QUERY_PORT" "$INSTALL_DIR" --game-port "$PORT")
  if [[ "${1:-}" == quick ]]; then observation_args+=(--quick); fi
  if [[ "$RUNTIME_BACKEND" == docker ]]; then
    local doctor_json
    doctor_json="$(ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" \
      "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" doctor --json)"
    container="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("runtime", {}).get("container_name", ""))' <<< "$doctor_json")"
    if [[ -n "$container" ]]; then observation_args+=(--container "$container"); fi
  fi
  "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/wreckfestserver_diagnostics.py" "${observation_args[@]}"
}

cleanup() {
  local original_status=$?
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    if [[ "$original_status" != 0 ]]; then diagnose_wreckfest; fi
    if ! run_alphagsm "$SERVER_NAME" stop; then
      echo "Wreckfest cleanup could not stop the server; retaining active payloads" >&2
      return 1
    fi
    SERVER_STARTED=0
  fi
  if [[ "${WORKSHOP_CONFIGURED:-0}" == "1" ]]; then
    run_alphagsm "$SERVER_NAME" mod cleanup
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
case "$RUNTIME_BACKEND" in
  docker) require_cmd docker ;;
  process) require_cmd xvfb-run ;;
  *) echo "ALPHAGSM_TEST_RUNTIME_BACKEND must be process, docker, or auto" >&2; exit 1 ;;
esac

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" wreckfest-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/wreckfest-server"
CONFIG_PATH="$WORK_DIR/alphagsm-wreckfest.conf"
IMAGE=""
if [[ "$RUNTIME_BACKEND" == docker ]]; then
  IMAGE="$(resolve_runtime_image)"
fi

mkdir -p "$HOME_DIR"
PORT="$(pick_free_port)"
QUERY_PORT="$(pick_free_port)"
while [[ "$QUERY_PORT" == "$PORT" ]]; do
  QUERY_PORT="$(pick_free_port)"
done
STEAM_PORT="$(pick_free_port)"
while [[ "$STEAM_PORT" == "$PORT" || "$STEAM_PORT" == "$QUERY_PORT" ]]; do
  STEAM_PORT="$(pick_free_port)"
done

cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR

[downloader]
db_path = $HOME_DIR/downloads/downloads.txt
target_path = $HOME_DIR/downloads/downloads

[downloader.steamcmd]
steamcmd_path = $WORK_DIR/steamcmd

[server]
datapath = $HOME_DIR/conf

[runtime]
backend = $RUNTIME_BACKEND

[process]
backend = subprocess

[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-Wreckfest-Smoke#
keeplogs = 1

[docker]
image_wine_proton = $IMAGE
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using query port: $QUERY_PORT"
echo "Using steam port: $STEAM_PORT"
echo "Using image: $IMAGE"

run_create_or_skip_disabled "$SERVER_NAME" create wreckfestserver
run_alphagsm "$SERVER_NAME" set wineprefix "$INSTALL_DIR/.alphagsm-wineprefix"
run_alphagsm "$SERVER_NAME" set queryport "$QUERY_PORT"
run_alphagsm "$SERVER_NAME" set steamport "$STEAM_PORT"
run_alphagsm "$SERVER_NAME" set servername "AlphaGSM Wreckfest Smoke"
run_alphagsm "$SERVER_NAME" set maxplayers 16
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == 1 ]]; then
  WORKSHOP_CONFIGURED=1
  run_alphagsm "$SERVER_NAME" mod add workshop 3428792631
  run_alphagsm "$SERVER_NAME" mod apply
  run_alphagsm "$SERVER_NAME" set track crazy_2000_classic
fi
SERVER_STARTED=1
run_alphagsm "$SERVER_NAME" start
diagnose_wreckfest quick || true
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
if [[ "$WORKSHOP_CONFIGURED" == 1 ]]; then
  run_alphagsm "$SERVER_NAME" send tracks
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" \
    "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" logs -n 2000 > "$WORK_DIR/workshop-engine.log"
  "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/wreckfestserver_workshop.py" "$WORK_DIR/workshop-engine.log"
fi
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" stop
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" status
if [[ "$WORKSHOP_CONFIGURED" == 1 ]]; then
  run_alphagsm "$SERVER_NAME" mod cleanup
  WORKSHOP_CONFIGURED=0
fi
