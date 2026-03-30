FROM ubuntu:22.04

# Prevent apt from asking questions
ARG DEBIAN_FRONTEND=noninteractive

# All system packages the integration tests need, baked into the image so each
# test runner starts ready to go without a per-job apt-get install.
#
#   wine64 / wine32:i386 / winetricks  — run Windows-only game server binaries
#   screen                              — AlphaGSM's process supervisor
#   lib32gcc-s1 lib32stdc++6           — 32-bit runtime (Source engine servers)
#   p7zip-full                          — .7z archive support
#   curl python3 wget ca-certificates  — used by install_proton.sh fallback path
RUN dpkg --add-architecture i386 \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        wine64 wine32:i386 winetricks \
        screen \
        lib32gcc-s1 lib32stdc++6 \
        p7zip-full \
        curl python3 wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Put the Wine prefix at a fixed, HOME-agnostic path.  GitHub Actions sets HOME
# to /github/home or /root depending on the container user; using /opt/wine
# avoids any ambiguity.  Integration-test jobs inherit WINEPREFIX from this ENV
# so Wine always finds the pre-built prefix regardless of runner user.
ENV WINEPREFIX=/opt/wine
ENV DISPLAY=""
ENV WINEDLLOVERRIDES="winex11.drv="
ENV WINEDEBUG=-all

# Initialise the Wine prefix and install common Windows runtimes.
# wineserver --kill ensures the background wineserver exits cleanly before
# Docker commits the layer; || true keeps it non-fatal if none is running.
RUN wineboot --init \
 && winetricks -q win10 \
 && (winetricks -q --force vcrun2019 || true) \
 && (wineserver --kill || true)

# Wine Mono (.NET/CLR runtime required by .NET-based game servers such as
# Medieval Engineers and Space Engineers).
RUN wget -q \
        "https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi" \
        -O /tmp/wine-mono.msi \
 && wine msiexec /i /tmp/wine-mono.msi /qn \
 && (wineserver --kill || true) \
 && rm -f /tmp/wine-mono.msi

# Install Proton-GE into /opt/proton-ge, which is already listed in the
# _PROTON_SEARCH_DIRS tuple in src/utils/proton.py so all game modules find it
# automatically without any additional configuration.
#
# GH_TOKEN is injected as a BuildKit secret so it never lands in any image
# layer.  install_proton.sh uses it via the curl+python fallback when gh CLI is
# not present; the fallback adds "Authorization: Bearer $GITHUB_TOKEN" to the
# GitHub API request, raising the rate limit from 60 to 5000 req/h.
COPY scripts/install_proton.sh /tmp/install_proton.sh
RUN --mount=type=secret,id=gh_token \
    GH_TOKEN=$(cat /run/secrets/gh_token 2>/dev/null || true) \
    GITHUB_TOKEN=${GH_TOKEN} \
    PROTON_GE_DIR=/opt/proton-ge \
    bash /tmp/install_proton.sh proton \
 && rm -f /tmp/install_proton.sh
