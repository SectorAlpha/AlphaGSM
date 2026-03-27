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
    sudo apt-get update -qq
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
        ;;
    proton)
        install_proton_ge
        ;;
    full|*)
        install_wine
        install_proton_ge
        ;;
esac

echo ""
echo "==> Installation complete."
echo "    To verify Wine:     wine --version"
echo "    To verify Proton:   ls -la ${PROTON_GE_DIR:-$HOME/.local/share/proton-ge}/"
