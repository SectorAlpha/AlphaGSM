#!/usr/bin/env bash
set -euo pipefail

WINEPREFIX_PATH="${ALPHAGSM_WINEPREFIX:-/srv/server/.alphagsm-wineprefix}"
PROTON_BIN="${ALPHAGSM_PROTON_BIN:-/opt/proton-ge/proton}"
NATIVE_COMMAND="${1:-}"
XVFB_ENABLED="${ALPHAGSM_XVFB:-0}"
XVFB_DISPLAY="${ALPHAGSM_XVFB_DISPLAY:-:99}"
XVFB_SERVER_ARGS="${ALPHAGSM_XVFB_SERVER_ARGS:--screen 0 1024x768x24 -nolisten tcp}"
XVFB_AUTH_DIR=""
XVFB_AUTH_FILE=""
XVFB_PID=""

ensure_xdg_runtime_dir() {
    if [[ -z "${XDG_RUNTIME_DIR:-}" || ! -d "${XDG_RUNTIME_DIR:-}" ]]; then
        export XDG_RUNTIME_DIR="/tmp/alphagsm-xdg-runtime"
    fi

    mkdir -p "${XDG_RUNTIME_DIR}"
    chmod 700 "${XDG_RUNTIME_DIR}" >/dev/null 2>&1 || true
}

bootstrap_wineprefix() {
    if [[ ! -d "/opt/wine" ]]; then
        mkdir -p "${WINEPREFIX_PATH}"
        return
    fi

    mkdir -p "${WINEPREFIX_PATH}"

    if [[ ! -f "${WINEPREFIX_PATH}/system.reg" || ! -d "${WINEPREFIX_PATH}/drive_c/windows/mono/mono-2.0" ]]; then
        cp -a --update=none /opt/wine/. "${WINEPREFIX_PATH}/"
    fi
}

if [[ -n "${NATIVE_COMMAND}" && "${NATIVE_COMMAND##*.}" != "exe" ]]; then
    if command -v "${NATIVE_COMMAND}" >/dev/null 2>&1 || [[ -x "${NATIVE_COMMAND}" ]]; then
        exec "$@"
    fi
fi

bootstrap_wineprefix

export DISPLAY="${DISPLAY:-}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES-winex11.drv=}"
ensure_xdg_runtime_dir

cleanup_xvfb() {
    if [[ -n "${XVFB_PID}" ]]; then
        kill "${XVFB_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${XVFB_AUTH_DIR}" ]]; then
        rm -rf "${XVFB_AUTH_DIR}" >/dev/null 2>&1 || true
    fi
}

start_xvfb() {
    XVFB_AUTH_DIR="$(mktemp -d -t alphagsm-xvfb.XXXXXX)"
    XVFB_AUTH_FILE="${XVFB_AUTH_DIR}/Xauthority"
    touch "${XVFB_AUTH_FILE}"
    xauth -f "${XVFB_AUTH_FILE}" add "${XVFB_DISPLAY}" . "$(mcookie)" >/dev/null 2>&1
    Xvfb "${XVFB_DISPLAY}" ${XVFB_SERVER_ARGS} -auth "${XVFB_AUTH_FILE}" >/tmp/alphagsm-xvfb.log 2>&1 &
    XVFB_PID="$!"
    for _attempt in $(seq 1 100); do
        if [[ -S "/tmp/.X11-unix/X${XVFB_DISPLAY#:}" ]]; then
            export DISPLAY="${XVFB_DISPLAY}"
            export XAUTHORITY="${XVFB_AUTH_FILE}"
            return 0
        fi
        sleep 0.1
    done
    echo "AlphaGSM wine-proton entrypoint: Xvfb failed to become ready on ${XVFB_DISPLAY}" >&2
    cleanup_xvfb
    exit 1
}

run_windows_command() {
    if [[ "${ALPHAGSM_PREFER_PROTON:-0}" == "1" && -x "${PROTON_BIN}" ]]; then
        export STEAM_COMPAT_DATA_PATH="${WINEPREFIX_PATH}"
        export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-}"
        "${PROTON_BIN}" run "$@"
        return
    fi

    export WINEPREFIX="${WINEPREFIX_PATH}"

    if command -v wine64 >/dev/null 2>&1; then
        wine64 "$@"
        return
    fi

    wine "$@"
}

if [[ "${XVFB_ENABLED}" == "1" ]]; then
    trap cleanup_xvfb EXIT
    start_xvfb
    run_windows_command "$@"
    exit $?
fi

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
