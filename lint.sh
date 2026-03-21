#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DIRS=(
  core
  downloader
  downloadermodules
  gamemodules
  screen
  server
  utils
)

if command -v rg >/dev/null 2>&1; then
  mapfile -t files < <(rg --files "${DIRS[@]}" -g '*.py' -g '!downloadermodules/steamcmd.py')
else
  mapfile -t files < <(find "${DIRS[@]}" -type f -name '*.py' ! -path 'downloadermodules/steamcmd.py' | sort)
fi

PYTHONPATH="${PYTHONPATH:-.}" "$PYTHON_BIN" -m pylint --fail-under=10 "${files[@]}"
