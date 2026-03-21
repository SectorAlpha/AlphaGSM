#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DIRS=(
  src/core
  src/downloader
  src/downloadermodules
  src/gamemodules
  src/screen
  src/server
  src/utils
)

if command -v rg >/dev/null 2>&1; then
  mapfile -t files < <(rg --files "${DIRS[@]}" -g '*.py' -g '!src/downloadermodules/steamcmd.py')
else
  mapfile -t files < <(find "${DIRS[@]}" -type f -name '*.py' ! -path 'src/downloadermodules/steamcmd.py' | sort)
fi

PYTHONPATH="${PYTHONPATH:-.:src}" "$PYTHON_BIN" -m pylint --fail-under=10 "${files[@]}"
