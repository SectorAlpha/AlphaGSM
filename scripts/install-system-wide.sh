#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/usr/local/lib/alphagsm}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
SBIN_DIR="${SBIN_DIR:-/usr/local/sbin}"
CONFIG_PATH="${CONFIG_PATH:-/etc/alphagsm.conf}"
SUDOERS_PATH="${SUDOERS_PATH:-/etc/sudoers.d/gameservers}"
ALPHAGSM_USER="${ALPHAGSM_USER:-alphagsm}"
ALPHAGSM_HOME="${ALPHAGSM_HOME:-/home/$ALPHAGSM_USER}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "This installer must be run as root." >&2
  exit 1
fi

if ! id "$ALPHAGSM_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$ALPHAGSM_HOME" --shell /usr/sbin/nologin "$ALPHAGSM_USER"
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$SBIN_DIR" "$ALPHAGSM_HOME/gitlive" "$ALPHAGSM_HOME/downloads"

cp -a "$REPO_ROOT"/. "$INSTALL_ROOT"/

if [[ ! -f "$CONFIG_PATH" ]]; then
  cp "$INSTALL_ROOT/alphagsm.conf-template" "$CONFIG_PATH"
fi

ln -sfn "$INSTALL_ROOT/alphagsm" "$BIN_DIR/alphagsm"
install -m 0755 "$INSTALL_ROOT/scripts/gitalphagsm" "$SBIN_DIR/gitalphagsm"

cat >"$SUDOERS_PATH" <<EOF
%alphagsm       ALL = ($ALPHAGSM_USER) NOPASSWD:$INSTALL_ROOT/alphagsm-downloads
EOF
chmod 0440 "$SUDOERS_PATH"

chown -R "$ALPHAGSM_USER":"$ALPHAGSM_USER" "$ALPHAGSM_HOME"

cat <<EOF
AlphaGSM system-wide install complete.

System config:
  $CONFIG_PATH

Shared download user:
  $ALPHAGSM_USER

Shared directories:
  $ALPHAGSM_HOME/gitlive
  $ALPHAGSM_HOME/downloads

Code install root:
  $INSTALL_ROOT

Shared command:
  $BIN_DIR/alphagsm

Root git helper:
  $SBIN_DIR/gitalphagsm

Sudoers file:
  $SUDOERS_PATH
EOF
