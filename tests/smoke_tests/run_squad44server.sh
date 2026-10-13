#!/usr/bin/env bash
set -Eeuo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-900}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itsquad44server}"
SERVER_STARTED=0
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-docker}"
ALPHAGSM_WORK_DIR="${ALPHAGSM_WORK_DIR:-$REPO_ROOT/build/workshop-validation/squad44server}"
export ALPHAGSM_WORK_DIR

run_alphagsm() {
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  local rc=$?
  set +e
  if [[ "$SERVER_STARTED" == "1" ]]; then
    run_alphagsm "$SERVER_NAME" stop
  fi
  return "$rc"
}
trap cleanup EXIT

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" squad44server-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/home"
INSTALL_DIR="$WORK_DIR/server"
CONFIG_PATH="$WORK_DIR/alphagsm.conf"
mkdir -p "$HOME_DIR"
PORT="$(pick_free_port_group 2)"
QUERY_PORT="$((PORT + 1))"

cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR
[downloader]
db_path = $HOME_DIR/downloads.txt
target_path = $HOME_DIR/downloads
[downloader.steamcmd]
steamcmd_path = $WORK_ROOT/steamcmd
[server]
datapath = $HOME_DIR/conf
[runtime]
backend = $RUNTIME_BACKEND
[process]
backend = subprocess
[docker]
backend = subprocess
EOF

run_alphagsm "$SERVER_NAME" create squad44server
if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX:-}" ]]; then
  run_alphagsm "$SERVER_NAME" set image "$ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX"
fi
run_alphagsm "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
run_alphagsm "$SERVER_NAME" mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2909251852
run_alphagsm "$SERVER_NAME" mod apply
run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" a2s "$START_TIMEOUT_SECONDS"
"$PYTHON_BIN" - "$INSTALL_DIR" <<'PY'
from pathlib import Path
import re
import sys
logs = Path(sys.argv[1]) / "PostScriptum/Saved/Logs"
assert any(re.search(r"LogPakFile:.*Mounted Pak file.*SquidBots.*\.pak", path.read_text(errors="replace"))
           for path in logs.glob("*.log")), "Fresh engine log did not prove native Workshop PAK mounting"
PY
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" stop
SERVER_STARTED=0
"$PYTHON_BIN" - "$QUERY_PORT" "$STOP_TIMEOUT_SECONDS" <<'PY'
import socket
import sys
import time
deadline = time.monotonic() + int(sys.argv[2])
while time.monotonic() < deadline:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        try:
            sock.sendto(b"\xff\xff\xff\xffTSource Engine Query\0", ("127.0.0.1", int(sys.argv[1])))
            sock.recv(4096)
        except OSError:
            break
    time.sleep(1)
else:
    raise SystemExit("Native A2S query port still responds after stop")
PY
run_alphagsm "$SERVER_NAME" mod cleanup
run_alphagsm "$SERVER_NAME" status
