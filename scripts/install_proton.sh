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

    echo "    Setting Windows version to Windows 10..."
    # Default Wine prefix is Win7; many modern game servers need Win10 APIs.
    # This prevents 'kernelbase.dll bad index' crashes on newer binaries.
    WINEDEBUG=-all winetricks win10

    echo "    Installing Visual C++ 2019 runtime (vcrun2019)..."
    # WINEDEBUG=-all suppresses Wine's verbose debug chatter on first-run.
    WINEDEBUG=-all winetricks --unattended vcrun2019

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

    # Resolve the latest tarball URL via the GitHub releases API.
    RELEASE_API="https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"
    ASSET_URL=$(
        curl -sf "$RELEASE_API" \
            -H "Accept: application/vnd.github.v3+json" |
        python3 - <<'EOF'
import json, sys
data = json.load(sys.stdin)
for asset in data.get("assets", []):
    if asset["name"].endswith(".tar.gz"):
        print(asset["browser_download_url"])
        break
EOF
    )

    if [ -z "$ASSET_URL" ]; then
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
