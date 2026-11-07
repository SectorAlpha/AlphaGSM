set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-300}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itcodwawserv}"
SERVER_STARTED=0
LOCAL_DOCKER_IMAGE="alphagsm-steamcmd-linux-runtime:local"
PUBLISHED_DOCKER_IMAGE="ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

run_alphagsm() {
  echo >&2
  echo "=== alphagsm $* ===" >&2
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

resolve_docker_image() {
  if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX:-}" ]]; then
    printf '%s\n' "$ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX"
    return 0
  fi

  if docker image inspect "$LOCAL_DOCKER_IMAGE" >/dev/null 2>&1; then
    printf '%s\n' "$LOCAL_DOCKER_IMAGE"
    return 0
  fi

  printf '%s\n' "$PUBLISHED_DOCKER_IMAGE"
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"


wait_for_codwaw_stopped() {
  "$PYTHON_BIN" - "$PORT" "$STOP_TIMEOUT_SECONDS" <<'PYCLOSED'
import socket
import sys
import time

port, timeout = map(int, sys.argv[1:])
pending = {"tcp", "udp"}
deadline = time.monotonic() + timeout
while pending and time.monotonic() < deadline:
    for protocol in tuple(pending):
        try:
            if protocol == "tcp":
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    pass
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(1)
                    sock.connect(("127.0.0.1", port))
                    sock.send(b"\xff\xff\xff\xffgetstatus\n")
                    sock.recv(4096)
        except ConnectionRefusedError:
            pending.remove(protocol)
        except socket.timeout:
            pass
    if pending:
        time.sleep(1)
if pending:
    raise SystemExit(f"CoDWaW listeners still open after stop: {sorted(pending)}")
PYCLOSED
}


cleanup() {
  local rc=$?
  set +e
  if [[ "$rc" -ne 0 && -n "${INSTALL_DIR:-}" ]]; then
    capture_application_logs "$INSTALL_DIR"/Saved/Logs/*.log "$INSTALL_DIR"/*/Saved/Logs/*.log
    capture_runtime_diagnostics "$SERVER_NAME"
  fi
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd docker

DOCKER_IMAGE="$(resolve_docker_image)"

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" codwawserver-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/codwawserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-codwawserver.conf"

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
sessiontag = AlphaGSM-codwawserv-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create codwawserver
run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"
# The isolated local server uses native LAN mode; Internet mode depends on
# DemonWare authentication and DNS. Operator servers retain default mode 2.
run_alphagsm "$SERVER_NAME" set dedicated 1
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "quake" "$START_TIMEOUT_SECONDS" "$PORT"
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
INFO_JSON="$(run_alphagsm "$SERVER_NAME" info --json)"
printf '%s\n' "$INFO_JSON"
"$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data["protocol"] == "quake" and data["port"] == int(sys.argv[1]), data
assert data["map"] == "mp_airfield" and data["players"] == 0, data
assert isinstance(data["max_players"], int) and data["max_players"] > 0, data
' "$PORT" <<< "$INFO_JSON"
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

wait_for_codwaw_stopped
STATUS_OUTPUT="$(run_alphagsm "$SERVER_NAME" status)"
printf '%s\n' "$STATUS_OUTPUT"
[[ "$STATUS_OUTPUT" == *"isn't running"* ]]
