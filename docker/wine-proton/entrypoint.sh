#!/usr/bin/env bash
set -euo pipefail

WINEPREFIX_PATH="${ALPHAGSM_WINEPREFIX:-/srv/server/.alphagsm-wineprefix}"
PROTON_BIN="${ALPHAGSM_PROTON_BIN:-/opt/proton-ge/proton}"

mkdir -p "${WINEPREFIX_PATH}"

export DISPLAY="${DISPLAY:-}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winex11.drv=}"

if [[ "${ALPHAGSM_PREFER_PROTON:-0}" == "1" && -x "${PROTON_BIN}" ]]; then
    export STEAM_COMPAT_DATA_PATH="${WINEPREFIX_PATH}"
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-}"
    exec "${PROTON_BIN}" run "$@"
fi

export WINEPREFIX="${WINEPREFIX_PATH}"

if command -v wine64 >/dev/null 2>&1; then
    exec wine64 "$@"
fi

exec wine "$@"
