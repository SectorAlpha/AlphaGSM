#!/usr/bin/env bash

# Copy AlphaGSM under /usr/local and point it at /etc/alphagsm.conf.
# Code installed under /usr uses that system file. Each operator's servers
# stay in that operator's home. The download cache is shared.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/usr/local/lib/alphagsm}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
SBIN_DIR="${SBIN_DIR:-/usr/local/sbin}"
CONFIG_PATH="${CONFIG_PATH:-/etc/alphagsm.conf}"
SUDOERS_PATH="${SUDOERS_PATH:-/etc/sudoers.d/gameservers}"
ALPHAGSM_USER="${ALPHAGSM_USER:-alphagsm}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "This installer must be run as root." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to write /etc/alphagsm.conf." >&2
  exit 1
fi

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

if ! id "$ALPHAGSM_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/home/$ALPHAGSM_USER" --shell /usr/sbin/nologin "$ALPHAGSM_USER"
fi

ALPHAGSM_HOME="$(getent passwd "$ALPHAGSM_USER" | cut -d: -f6)"
ALPHAGSM_GROUP="$(id -gn "$ALPHAGSM_USER")"
if [[ -z "$ALPHAGSM_HOME" || "$ALPHAGSM_HOME" == "/" ]]; then
  echo "Refusing empty or root home for $ALPHAGSM_USER" >&2
  exit 1
fi

mkdir -p \
  "$INSTALL_ROOT" \
  "$BIN_DIR" \
  "$SBIN_DIR" \
  "$ALPHAGSM_HOME/gitlive" \
  "$ALPHAGSM_HOME/downloads/downloads"

tar -C "$REPO_ROOT" \
  --exclude=alphagsm.conf \
  --exclude=env \
  --exclude=.venv \
  --exclude=__pycache__ \
  -cf - . | tar -C "$INSTALL_ROOT" -xf -

if [[ ! -f "$CONFIG_PATH" ]]; then
  cp "$INSTALL_ROOT/alphagsm.conf-template" "$CONFIG_PATH"
  CONFIG_PATH="$CONFIG_PATH" ALPHAGSM_USER="$ALPHAGSM_USER" ALPHAGSM_HOME="$ALPHAGSM_HOME" \
    python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["CONFIG_PATH"])
user = os.environ["ALPHAGSM_USER"]
home = os.environ["ALPHAGSM_HOME"]
text = path.read_text(encoding="utf-8")
header = "[downloader]\n"
start = text.find(header)
if start < 0:
    raise SystemExit("alphagsm.conf has no [downloader] section")
body_start = start + len(header)
rest = text[body_start:]
end = rest.find("\n[")
body = rest if end < 0 else rest[:end]
if any(line.startswith("user ") or line.startswith("user=") for line in body.splitlines()):
    raise SystemExit(0)
block = (
    f"user = {user}\n"
    f"db_path = {home}/downloads/downloads.txt\n"
    f"target_path = {home}/downloads/downloads\n"
)
path.write_text(text[:body_start] + block + text[body_start:], encoding="utf-8")
PY
fi

ln -sfn "$INSTALL_ROOT/alphagsm" "$BIN_DIR/alphagsm"
install -m 0755 "$INSTALL_ROOT/scripts/gitalphagsm" "$SBIN_DIR/gitalphagsm"

cat >"$SUDOERS_PATH" <<EOF
%$ALPHAGSM_GROUP ALL = ($ALPHAGSM_USER) NOPASSWD:$INSTALL_ROOT/alphagsm-downloads
EOF
chmod 0440 "$SUDOERS_PATH"
if command -v visudo >/dev/null 2>&1; then
  visudo -cf "$SUDOERS_PATH"
fi

chown -R "$ALPHAGSM_USER:$ALPHAGSM_GROUP" "$ALPHAGSM_HOME"

cat <<EOF
AlphaGSM system-wide install complete.

System config:
  $CONFIG_PATH

Shared download account:
  $ALPHAGSM_USER ($ALPHAGSM_HOME)

Shared download cache:
  $ALPHAGSM_HOME/downloads/downloads.txt
  $ALPHAGSM_HOME/downloads/downloads

Operator checkout directory, unused by the running command:
  $ALPHAGSM_HOME/gitlive

Code install root:
  $INSTALL_ROOT

Shared command:
  $BIN_DIR/alphagsm

Root git helper:
  $SBIN_DIR/gitalphagsm

Sudoers file:
  $SUDOERS_PATH

Add each operator to the $ALPHAGSM_GROUP group so shared downloads do not prompt:
  usermod -aG $ALPHAGSM_GROUP USER
EOF
