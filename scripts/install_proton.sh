#!/usr/bin/env bash
# Install Wine and Proton-GE for running Windows game servers on Linux.
#
# Usage:
#   bash scripts/install_proton.sh            # installs Wine + Proton-GE (latest)
#   bash scripts/install_proton.sh wine       # installs Wine only
#   bash scripts/install_proton.sh proton     # installs Proton-GE only
#
# Environment variables:
#   PROTON_GE_DIR  — override the Proton-GE install directory
#                    (default: ~/.local/share/proton-ge)

set -euo pipefail

MODE="${1:-full}"

# ---------------------------------------------------------------------------
# Wine prefix setup — installs required Windows runtimes via winetricks
# ---------------------------------------------------------------------------
# Many Windows game server binaries require the Microsoft Visual C++ runtime.
# We install it into the default Wine prefix (~/.wine) once after Wine is first
# set up.  winetricks is idempotent: it skips packages already installed.

setup_wine_prefix() {
    echo "==> Setting up Wine prefix (installing common Windows runtimes)..."

    if ! command -v winetricks >/dev/null 2>&1; then
        echo "    Installing winetricks..."
        sudo apt-get install -y winetricks -qq
    fi

    # Force Wine to use its built-in null/headless renderer for all prefix
    # initialisation work.  Dedicated game servers never need a display.
    #   DISPLAY=                     — no X display
    #   WINEDLLOVERRIDES=winex11.drv= — override X11 driver with nothing,
    #                                   activating Wine's null renderer even
    #                                   if DISPLAY is set in the outer env
    #   WINEDEBUG=-all               — silence Wine's verbose debug chatter
    export DISPLAY=""
    export WINEDLLOVERRIDES="winex11.drv="
    export WINEDEBUG=-all

    echo "    Initialising Wine prefix..."
    wineboot --init

    echo "    Setting Windows version to Windows 10..."
    # Default Wine prefix is Win7; many modern game servers need Win10 APIs.
    # This prevents 'kernelbase.dll bad index' crashes on newer binaries.
    # -q suppresses any installer dialogs (null renderer makes this redundant
    # but it is good practice regardless).
    winetricks -q win10

    echo "    Installing Visual C++ 2019 runtime (vcrun2019)..."
    # --force bypasses SHA256 verification: Microsoft periodically updates the
    # VC redist installer at the same aka.ms URL, causing winetricks' expected
    # hash to become stale.  The URL itself is trusted.  || true keeps this
    # non-fatal; not every server needs vcrun2019.
    winetricks -q --force vcrun2019 || true

    echo "    Installing Wine Mono (.NET/CLR runtime for managed-code servers)..."
    # .NET-based servers (e.g. Medieval Engineers, Space Engineers) need Wine Mono.
    # The MSI is downloaded from WineHQ; winetricks verb 'mono' is unavailable
    # in newer winetricks — we install directly via msiexec instead.
    local mono_msi_url="https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi"
    local mono_msi="/tmp/wine-mono-8.1.0.msi"
    if ! ls ~/.wine/drive_c/windows/mono/mono-2.0 >/dev/null 2>&1; then
        echo "    Downloading Wine Mono MSI..."
        wget -q "$mono_msi_url" -O "$mono_msi"
        wine msiexec /i "$mono_msi" /qn
        rm -f "$mono_msi"
    else
        echo "    Wine Mono already installed — skipping."
    fi

    echo "    Wine prefix ready."
}

# ---------------------------------------------------------------------------
# Wine
# ---------------------------------------------------------------------------

install_wine() {
    echo "==> Checking Wine..."
    if command -v wine >/dev/null 2>&1; then
        echo "    Wine is already installed: $(wine --version)"
        return
    fi

    echo "==> Installing Wine from apt..."
    if ! sudo dpkg --add-architecture i386 2>/dev/null; then
        echo "    WARNING: could not add i386 architecture (may already be present)"
    fi
    # || true: ignore errors from broken third-party repos (e.g. missing Release
    # files); Wine itself comes from the main Ubuntu archive which is unaffected.
    sudo apt-get update -qq || true
    sudo apt-get install -y wine64 wine32:i386

    echo "    Wine installed: $(wine --version)"
}

# ---------------------------------------------------------------------------
# Proton-GE (standalone – does not require Steam)
# ---------------------------------------------------------------------------

install_proton_ge() {
    echo "==> Installing Proton-GE..."

    PROTON_INSTALL_DIR="${PROTON_GE_DIR:-$HOME/.local/share/proton-ge}"
    mkdir -p "$PROTON_INSTALL_DIR"

    # Resolve the download URL for the latest Proton-GE tarball.
    # Prefer the gh CLI (pre-installed and pre-authenticated in GitHub Actions)
    # over raw curl to avoid unauthenticated API rate limits (60 req/h).
    ASSET_URL=""
    RELEASE_API="https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"

    if command -v gh >/dev/null 2>&1; then
        ASSET_URL=$(
            gh release view --repo GloriousEggroll/proton-ge-custom \
                --json assets \
                --jq '[.assets[] | select(.name | endswith(".tar.gz")) | .browserDownloadUrl] | first' \
                2>/dev/null || true
        )
    fi

    # Fall back to curl + python when gh is unavailable (local installs).
    if [ -z "${ASSET_URL:-}" ]; then
        AUTH_HEADER=()
        if [ -n "${GITHUB_TOKEN:-}" ]; then
            AUTH_HEADER=(-H "Authorization: Bearer $GITHUB_TOKEN")
        fi

        ASSET_URL=$(
            set +o pipefail  # don't abort if curl fails; handle below
            curl -s "$RELEASE_API" \
                -H "Accept: application/vnd.github.v3+json" \
                "${AUTH_HEADER[@]}" |
            python3 - <<'EOF'
import json, sys
body = sys.stdin.read()
try:
    data = json.loads(body)
except json.JSONDecodeError:
    print(f"ERROR: GitHub API returned non-JSON: {body[:200]!r}", file=sys.stderr)
    raise
if "message" in data:
    print(f"ERROR: GitHub API error: {data['message']}", file=sys.stderr)
    raise SystemExit(1)
for asset in data.get("assets", []):
    if asset["name"].endswith(".tar.gz"):
        print(asset["browser_download_url"])
        break
EOF
            set -o pipefail
        )
    fi

    if [ -z "${ASSET_URL:-}" ]; then
        echo "ERROR: Could not resolve Proton-GE download URL from $RELEASE_API" >&2
        exit 1
    fi

    echo "    Downloading $ASSET_URL ..."
    curl -L "$ASSET_URL" | tar xz -C "$PROTON_INSTALL_DIR"

    # Verify the proton script landed correctly.
    PROTON_EXE=$(find "$PROTON_INSTALL_DIR" -maxdepth 2 -name "proton" -type f | sort -r | head -1)
    if [ -z "$PROTON_EXE" ]; then
        echo "ERROR: Proton executable not found after installation in $PROTON_INSTALL_DIR" >&2
        exit 1
    fi

    echo "    Proton-GE installed: $PROTON_EXE"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

case "$MODE" in
    wine)
        install_wine
        setup_wine_prefix
        ;;
    proton)
        install_proton_ge
        ;;
    full|*)
        install_wine
        install_proton_ge
        setup_wine_prefix
        ;;
esac

echo ""
echo "==> Installation complete."
echo "    To verify Wine:     wine --version"
echo "    To verify Proton:   ls -la ${PROTON_GE_DIR:-$HOME/.local/share/proton-ge}/"
echo "    To verify runtime:  ls ~/.wine/drive_c/windows/system32/vcruntime140.dll"
