#!/usr/bin/env bash
set -Eeuo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"
SERVER_NAME="${SERVER_NAME:-itasrdserver}"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
SERVER_STARTED=0
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-process}"
if [[ -z "${ALPHAGSM_TEST_RUNTIME_BACKEND:-}" ]] && \
   [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-}" || "${GITHUB_ACTIONS:-}" == true ]]; then
  RUNTIME_BACKEND=docker
fi
# This module declares a Docker runtime, so an explicit auto selection resolves to Docker.
if [[ "$RUNTIME_BACKEND" == auto ]]; then RUNTIME_BACKEND=docker; fi
case "$RUNTIME_BACKEND" in
  process|docker) ;;
  *) echo "Unsupported ASRD smoke runtime: $RUNTIME_BACKEND" >&2; exit 1 ;;
esac
RUNTIME_IMAGE="${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest}"
require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found for $RUNTIME_BACKEND runtime: $1" >&2
    exit 1
  }
}
run_alphagsm() {
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"
cleanup() {
  if [[ "${SERVER_STARTED:-0}" == 1 ]]; then run_alphagsm "$SERVER_NAME" stop || true; fi
}
trap cleanup EXIT
require_cmd "$PYTHON_BIN"
if [[ "$RUNTIME_BACKEND" == docker ]]; then
  require_cmd docker
else
  require_cmd screen
  require_cmd wine
fi
SMOKE_WORK_ROOT="${ALPHAGSM_WORK_DIR:-${TMPDIR:-/tmp}}"
mkdir -p "$SMOKE_WORK_ROOT"
WORK_DIR="$(mktemp -d "$SMOKE_WORK_ROOT/asrdserver-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/home"
INSTALL_DIR="$WORK_DIR/server"
CONFIG_PATH="$WORK_DIR/alphagsm.conf"
mkdir -p "$HOME_DIR"
PORT="$(pick_free_port_group 3)"
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
backend = screen
[docker]
backend = subprocess
image_wine_proton = $RUNTIME_IMAGE
[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-ASRD-Smoke#
keeplogs = 1
EOF
run_create_or_skip_disabled "$SERVER_NAME" create asrdserver
run_alphagsm "$SERVER_NAME" set clientport "$((PORT + 1))"
run_alphagsm "$SERVER_NAME" set sourcetvport "$((PORT + 2))"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
RCON_PASSWORD="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(20))')"
run_alphagsm "$SERVER_NAME" set rconpassword "$RCON_PASSWORD"
WORKSHOP_IDS=""
if [[ -n "${ASRD_WORKSHOP_COLLECTION:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$ASRD_WORKSHOP_COLLECTION"
elif [[ -n "${ASRD_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$ASRD_WORKSHOP_ITEM"
fi
if [[ -n "${ASRD_WORKSHOP_COLLECTION:-}${ASRD_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod apply
  WORKSHOP_IDS="$("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" <<'PYIDS'
import json, sys
with open(sys.argv[1]) as handle:
    print(" ".join(row["workshop_id"] for row in json.load(handle)["mods"]["desired"]["workshop"]))
PYIDS
)"
fi
SERVER_STARTED=1
run_alphagsm "$SERVER_NAME" start
wait_for_info_protocol "$SERVER_NAME" a2s "$START_TIMEOUT_SECONDS" "$PORT"
if [[ -n "${WORKSHOP_IDS:-}" ]]; then
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT" \
    ASRD_PROBE_PASSWORD="$RCON_PASSWORD" "$PYTHON_BIN" - "$ALPHAGSM_SCRIPT" "$SERVER_NAME" "$PORT" "${ASRD_WORKSHOP_LOAD_ITEM:-${WORKSHOP_IDS%% *}}" "${ASRD_WORKSHOP_MAP:-}" <<'PYLOAD'
import json, os, subprocess, sys, time
from tests.smoke_tests.asrd_workshop import query_native_maps, change_map
script, server, port, item, map_name = sys.argv[1:]
password = os.environ['ASRD_PROBE_PASSWORD']
deadline, selected, error = time.monotonic() + 300, False, None
while time.monotonic() < deadline:
    try:
        owners = query_native_maps('127.0.0.1', int(port), password)
        map_name = map_name or next((name for name, owner in owners.items() if owner == item), None)
        if map_name and owners.get(map_name) == item:
            if not selected:
                change_map('127.0.0.1', int(port), password, map_name)
                selected = True
            result = subprocess.run([sys.executable, script, server, 'info', '--json'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('protocol') == 'a2s' and data.get('map', '').lower() == map_name.lower():
                    assert query_native_maps('127.0.0.1', int(port), password).get(map_name) == item
                    print(f'Engine executes {map_name} from native Workshop item {item}')
                    break
    except (OSError, ValueError, AssertionError) as exc:
        error = exc
    time.sleep(2)
else:
    raise AssertionError(f'Reactive Drop native Workshop map failed: {error}')
PYLOAD
fi
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" - "$PORT" <<'PYCLOSED'
import sys, time
from utils.query import a2s_info, QueryError
for _ in range(60):
    try:
        a2s_info('127.0.0.1', int(sys.argv[1]), timeout=1)
    except QueryError:
        break
    time.sleep(2)
else:
    raise AssertionError('Reactive Drop still answers A2S after stop')
PYCLOSED
run_alphagsm "$SERVER_NAME" status
if [[ -n "${WORKSHOP_IDS:-}" ]]; then run_alphagsm "$SERVER_NAME" mod cleanup; fi
