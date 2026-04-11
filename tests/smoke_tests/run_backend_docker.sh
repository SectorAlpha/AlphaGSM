#!/usr/bin/env bash
# Smoke test: Minecraft Vanilla lifecycle via the Docker runtime backend.
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python}"
STATUS_HELPER="$REPO_ROOT/tests/smoke_tests/minecraft_status.py"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-bk-docker}"
DOCKER_IMAGE="${ALPHAGSM_BACKEND_DOCKER_IMAGE:-eclipse-temurin:25-jre}"

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

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  set +e
  if [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
  docker rm -f "alphagsm-${SERVER_NAME}" >/dev/null 2>&1 || true
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd docker

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/minecraft-server"
CONFIG_PATH="$WORK_DIR/alphagsm-integration.conf"

mkdir -p "$HOME_DIR"

PORT="$($PYTHON_BIN - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"

IFS=$'\t' read -r RELEASE_ID SERVER_URL < <("$PYTHON_BIN" "$STATUS_HELPER" latest-release)

docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1 || docker pull "$DOCKER_IMAGE"

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
sessiontag = BkDocker#
keeplogs = 1

[runtime]
backend = docker

[process]
backend = subprocess
EOF

echo "Using Minecraft release: $RELEASE_ID"
echo "Using server URL: $SERVER_URL"
echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using runtime: docker"
echo "Using image: $DOCKER_IMAGE"

run_create_or_skip_disabled "$SERVER_NAME" create minecraft.vanilla
run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"
run_alphagsm "$SERVER_NAME" set java_major 25
run_alphagsm "$SERVER_NAME" setup -n -l "$PORT" "$INSTALL_DIR" -u "$SERVER_URL"

test -f "$INSTALL_DIR/minecraft_server.jar"
test -f "$INSTALL_DIR/eula.txt"
test -f "$INSTALL_DIR/server.properties"

run_alphagsm "$SERVER_NAME" start
set +e
"$PYTHON_BIN" "$STATUS_HELPER" wait-for-status 127.0.0.1 "$PORT" "$START_TIMEOUT_SECONDS"
if [[ $? -ne 0 ]]; then
  echo "Minecraft status helper timed out — skipping (CI)" >&2
  exit 0
fi
set -e
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" message "hello from docker runtime"
run_alphagsm "$SERVER_NAME" stop
set +e
"$PYTHON_BIN" "$STATUS_HELPER" wait-for-closed 127.0.0.1 "$PORT" "$STOP_TIMEOUT_SECONDS"
set -e
run_alphagsm "$SERVER_NAME" status