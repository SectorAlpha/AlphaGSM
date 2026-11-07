#!/usr/bin/env bash

# Copy AlphaGSM for one Linux account. The program reads alphagsm.conf from
# this install root because the code is not under /usr.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/.local/lib/alphagsm}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CONFIG_PATH="$INSTALL_ROOT/alphagsm.conf"

case "$INSTALL_ROOT" in
  "$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "INSTALL_ROOT must be outside the repository: $INSTALL_ROOT" >&2
    exit 1
    ;;
esac

if [[ ! -f "$REPO_ROOT/alphagsm.conf-template" ]]; then
  echo "Missing $REPO_ROOT/alphagsm.conf-template" >&2
  exit 1
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
tar -C "$REPO_ROOT" \
  --exclude=alphagsm.conf \
  --exclude=env \
  --exclude=.venv \
  --exclude=__pycache__ \
  -cf - . | tar -C "$INSTALL_ROOT" -xf -

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

Python packages are not installed by this script. From the repository, run:
  python3 -m pip install -r requirements-runtime.txt

If '$BIN_DIR' is not in your PATH, add this to your shell profile:
  export PATH="$BIN_DIR:\$PATH"
EOF
