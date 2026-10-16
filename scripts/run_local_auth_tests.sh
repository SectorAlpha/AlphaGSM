#!/usr/bin/env bash
# Run local Steam-auth and bring-your-own asset tests.
# Passwords, tokens, and Steam Guard codes are rejected and never stored.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODE="unit"
SUITE="all"
SERVERS=""
PROFILE=""
ASSETS=""
STATE_DIR="${ALPHAGSM_LOCAL_AUTH_STATE:-}"
WORK_DIR="${ALPHAGSM_LOCAL_WORK_DIR:-$ROOT/.local-tests/local-auth}"
CONFIRM_ALL=0

usage() {
    cat <<'EOF'
Usage: scripts/run_local_auth_tests.sh [unit|integration] [options]

Runs the local-only tests in local_tests/. CI never collects that directory.
The command accepts a Steam auth profile name or an owned-assets directory.
It does not accept a password, token, or Steam Guard code.

  unit              Import and recipe checks. No download and no login.
  integration       AlphaGSM create, setup, start, query, info, and stop.
                    Requires --server and either --profile or --assets.

Options:
  --suite auth|byo|all     Support list to read. Default: all.
  --server NAME            Module id. Repeat, or separate names with commas.
  --server all             Every server in the selected suite. Requires
                           --confirm-all. This can download many games.
  --confirm-all            Allow --server all.
  --profile NAME           Existing Steam auth profile name, such as owned.
  --state-dir PATH         Directory that already contains steam-auth/NAME.
                           Defaults to ~/.alphagsm when that profile exists.
  --assets PATH            Owned game files for setup --assets.
  --work-dir PATH          Disposable server files. Default:
                           .local-tests/local-auth, which git ignores.
  --help                   Show this help.

Examples:
  scripts/run_local_auth_tests.sh unit
  scripts/run_local_auth_tests.sh integration --suite byo --server q3server --profile owned
  scripts/run_local_auth_tests.sh integration --suite auth --server acserver --profile owned

Create the profile from a terminal before an authenticated setup:
  alphagsm steam-auth login owned YOUR_STEAM_USERNAME
EOF
}

reject_secrets() {
    local arg
    for arg in "$@"; do
        case "$arg" in
            --password|--token|--guard|--steam-password|--steam-guard|--username)
                echo "Refusing an auth secret on the command line. Pass only a profile name or an assets directory." >&2
                exit 2
                ;;
        esac
    done
}

require_profile_name() {
    if [[ ! "$PROFILE" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "Profile names use letters, numbers, underscores, and hyphens." >&2
        exit 2
    fi
}

reject_secrets "$@"

while [[ $# -gt 0 ]]; do
    case "$1" in
        unit|integration)
            MODE="$1"
            shift
            ;;
        --suite)
            SUITE="${2:-}"
            shift 2
            ;;
        --server)
            if [[ -n "$SERVERS" ]]; then
                SERVERS="$SERVERS,${2:-}"
            else
                SERVERS="${2:-}"
            fi
            shift 2
            ;;
        --profile)
            PROFILE="${2:-}"
            shift 2
            ;;
        --state-dir)
            STATE_DIR="${2:-}"
            shift 2
            ;;
        --assets)
            ASSETS="${2:-}"
            shift 2
            ;;
        --work-dir)
            WORK_DIR="${2:-}"
            shift 2
            ;;
        --confirm-all)
            CONFIRM_ALL=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument. Run with --help." >&2
            exit 2
            ;;
    esac
done

if [[ "${GITHUB_ACTIONS:-}" == "true" || "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
    echo "Refusing to run local Steam auth or BYO tests in CI." >&2
    exit 2
fi

case "$SUITE" in
    auth|byo|all) ;;
    *)
        echo "Suite must be auth, byo, or all." >&2
        exit 2
        ;;
esac

if [[ -n "$PROFILE" && -n "$ASSETS" ]]; then
    echo "Use either --profile or --assets." >&2
    exit 2
fi

if [[ -n "$PROFILE" ]]; then
    require_profile_name
    if [[ -z "$STATE_DIR" && -d "$HOME/.alphagsm/steam-auth/$PROFILE" ]]; then
        STATE_DIR="$HOME/.alphagsm"
    fi
    if [[ -z "$STATE_DIR" || ! -d "$STATE_DIR/steam-auth/$PROFILE" ]]; then
        echo "Profile '$PROFILE' was not found. Pass --state-dir for the directory that contains steam-auth/$PROFILE." >&2
        echo "Create it with: alphagsm steam-auth login $PROFILE YOUR_STEAM_USERNAME" >&2
        exit 2
    fi
fi

if [[ -n "$ASSETS" && ! -d "$ASSETS" ]]; then
    echo "Assets path must be an existing directory." >&2
    exit 2
fi

if [[ "$MODE" == "integration" ]]; then
    if [[ -z "$SERVERS" ]]; then
        echo "Integration runs need --server NAME, or --server all --confirm-all." >&2
        exit 2
    fi
    IFS=',' read -ra requested_servers <<< "$SERVERS"
    for requested_server in "${requested_servers[@]}"; do
        if [[ "$requested_server" == "all" && "$CONFIRM_ALL" != "1" ]]; then
            echo "Refusing to run every server without --confirm-all." >&2
            exit 2
        fi
        if [[ "$requested_server" == "all" && ${#requested_servers[@]} -gt 1 ]]; then
            echo "Use --server all by itself." >&2
            exit 2
        fi
    done
    if [[ -z "$PROFILE" && -z "$ASSETS" ]]; then
        echo "Integration runs need --profile NAME or --assets PATH." >&2
        exit 2
    fi
fi

export ALPHAGSM_RUN_LOCAL_TESTS=1
export ALPHAGSM_LOCAL_SUITE="$SUITE"
export ALPHAGSM_LOCAL_SERVERS="$SERVERS"
export ALPHAGSM_LOCAL_AUTH_PROFILE="$PROFILE"
export ALPHAGSM_LOCAL_ASSETS="$ASSETS"
export ALPHAGSM_LOCAL_AUTH_STATE="$STATE_DIR"
export ALPHAGSM_LOCAL_WORK_DIR="$WORK_DIR"

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
TARGET=(local_tests/test_auth_byo_contracts.py)
if [[ "$MODE" == "integration" ]]; then
    TARGET=(local_tests/test_auth_byo_lifecycle.py)
fi

exec "$PYTHON_BIN" -m pytest "${TARGET[@]}" -o timeout=0 -o norecursedirs= -p no:cacheprovider
