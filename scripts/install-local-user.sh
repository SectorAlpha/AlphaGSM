#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/.local/lib/alphagsm}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CONFIG_PATH="$INSTALL_ROOT/alphagsm.conf"

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

cp -a "$REPO_ROOT"/. "$INSTALL_ROOT"/

if [[ ! -f "$CONFIG_PATH" ]]; then
  cp "$INSTALL_ROOT/alphagsm.conf-template" "$CONFIG_PATH"
fi

ln -sfn "$INSTALL_ROOT/alphagsm" "$BIN_DIR/alphagsm"

cat <<EOF
AlphaGSM local install complete.

Install root:
  $INSTALL_ROOT

Command link:
  $BIN_DIR/alphagsm

Config file:
  $CONFIG_PATH

If '$BIN_DIR' is not in your PATH, add this to your shell profile:
  export PATH="$BIN_DIR:\$PATH"
EOF
