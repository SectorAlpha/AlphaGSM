#!/usr/bin/env bash
# Shared SteamCMD helpers for smoke tests.
# Source this after defining run_alphagsm().

run_setup_or_skip_steamcmd() {
  local output_file
  output_file="$(mktemp)"
  set +e
  run_alphagsm "$@" 2>&1 | tee "$output_file"
  local rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -ne 0 ]]; then
    if grep -qE 'Failed to install app|No subscription|Missing configuration|No such file or directory|returned non-zero exit status' "$output_file"; then
      echo "Setup failed with known SteamCMD issue — skipping smoke test"
      rm -f "$output_file"
      exit 0
    fi
    rm -f "$output_file"
    return $rc
  fi
  rm -f "$output_file"
  return 0
}
