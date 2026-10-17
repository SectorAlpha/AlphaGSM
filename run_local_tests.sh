#!/usr/bin/env bash
# Run local-only Steam-auth and bring-your-own tests from the repository root.
# CI does not call this script. Passwords, tokens, and Steam Guard codes are rejected.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/scripts/run_local_auth_tests.sh" "$@"
