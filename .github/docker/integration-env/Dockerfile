FROM ubuntu:24.04

# Prevent apt from asking questions
ARG DEBIAN_FRONTEND=noninteractive

# All system packages the integration tests need, baked into the image so each
# test runner starts ready to go without a per-job apt-get install.
#
#   wine64 / wine32:i386 / winetricks  — run Windows-only game server binaries
#   screen                              — AlphaGSM's process supervisor
#   xvfb xauth                          — headless X server wrapper required by
#                                         Core Keeper's launcher (xvfb-run);
#                                         xauth is needed by xvfb-run itself
#   lib32gcc-s1 lib32stdc++6           — 32-bit runtime (Source engine servers)
#   p7zip-full                          — .7z archive support
#   unzip bzip2                         — archive formats used by some servers
#   libatomic1                          — GCC atomics used by UE4 / Unity servers
#   libc++1                             — LLVM C++ runtime used by newer native
#                                         Linux dedicated servers such as Pavlov VR
#   libsdl2-2.0-0                       — SDL2 runtime loaded by UE4/Unity servers
#   libpulse0                           — PulseAudio client; Unity loads it dynamically
#                                         even in -batchmode, crashes if not present
#   libcurl3t64-gnutls                  — GnuTLS-flavoured libcurl; Mordhau (and
#                                         similar CryEngine servers) link against
#                                         libcurl-gnutls.so.4 specifically
#                                         (Ubuntu 24.04 renamed this package from
#                                         libcurl3-gnutls to libcurl3t64-gnutls)
#   curl python3 wget ca-certificates  — used by install_proton.sh fallback path
#   jq                                 — required by the UT99 installer script
RUN dpkg --add-architecture i386 \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        wine64 wine32:i386 winetricks \
       screen \
       xvfb xauth \
        lib32gcc-s1 lib32stdc++6 \
        p7zip-full \
        unzip bzip2 \
                             libatomic1 libc++1 libsdl2-2.0-0 \
        libpulse0 \
        libcurl3t64-gnutls \
       curl jq python3 python3-pip python3-venv wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# screen stores its session sockets in /run/screen.  Ubuntu's tmpfiles.d
# creates that directory on boot, but tmpfiles.d does not run in Docker.
# Create it explicitly so screen -dmS succeeds inside the container.
RUN mkdir -p /run/screen && chmod 777 /run/screen

# libssl1.1 — many UE4 dedicated server binaries are linked against OpenSSL 1.1.
# Ubuntu 24.04 ships only libssl3; we backport the .deb from the Ubuntu 20.04
# archive so they can open their required libssl.so.1.1 at runtime.
RUN wget -q \
        "http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb" \
        -O /tmp/libssl1.1.deb \
 && dpkg -i /tmp/libssl1.1.deb \
 && rm -f /tmp/libssl1.1.deb

# libssl1.0.0 — older UE4 servers (2017-2019, e.g. Battalion 1944, built against
# UE4.18-4.20) link against OpenSSL 1.0.x (libssl.so.1.0.0 / libcrypto.so.1.0.0).
# Ubuntu 18.04 (Bionic) is the last release to ship this package.
RUN wget -q \
        "http://security.ubuntu.com/ubuntu/pool/main/o/openssl1.0/libssl1.0.0_1.0.2n-1ubuntu5_amd64.deb" \
        -O /tmp/libssl1.0.0.deb \
 && dpkg -i /tmp/libssl1.0.0.deb \
 && rm -f /tmp/libssl1.0.0.deb

# libprotobuf10 — ATLAS still links against libprotobuf.so.10, which Ubuntu
# 24.04 no longer ships.  Pull the Bionic compatibility package directly so the
# process-backed CI image can still launch the native Linux server binary.
RUN wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/p/protobuf/libprotobuf10_3.0.0-9.1ubuntu1_amd64.deb" \
       -O /tmp/libprotobuf10.deb \
 && dpkg -i /tmp/libprotobuf10.deb \
 && rm -f /tmp/libprotobuf10.deb

# libidn11 — the same ATLAS Linux binary still depends on the legacy
# libidn.so.11 SONAME that Ubuntu 24.04 removed from the main archive.
RUN wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/libi/libidn/libidn11_1.33-2.2ubuntu2_amd64.deb" \
       -O /tmp/libidn11.deb \
 && dpkg -i /tmp/libidn11.deb \
 && rm -f /tmp/libidn11.deb

# Pavlov VR still requests the unversioned libc++.so name at runtime. Ubuntu's
# libc++-dev package provides only a linker script there, which the dynamic
# loader rejects, so point the loader name at the real libc++.so.1 ELF instead.
RUN ln -sf /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so

# Install Temurin 25 (Java 25) — required by the current Minecraft server
# bundler (net.minecraft.bundler.Main, class file version 69).  Ubuntu 24.04's
# openjdk-21-jdk-headless only handles class files up to version 65 (Java 21).
RUN wget -q -O /usr/share/keyrings/adoptium.asc \
        https://packages.adoptium.net/artifactory/api/gpg/key/public \
 && printf 'deb [arch=%s signed-by=/usr/share/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb %s main\n' \
        "$(dpkg --print-architecture)" \
        "$(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release)" \
        > /etc/apt/sources.list.d/adoptium.list \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends temurin-25-jdk \
 && rm -rf /var/lib/apt/lists/*

# Install the .NET 10 runtime — required by SS14's Linux apphost
# (Robust.Server).  Baking it into the integration image keeps it available
# under the non-root gsmuser account used by the integration-test job.
RUN wget -q \
       https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb \
       -O /tmp/packages-microsoft-prod.deb \
 && dpkg -i /tmp/packages-microsoft-prod.deb \
 && rm -f /tmp/packages-microsoft-prod.deb \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends dotnet-runtime-10.0 \
 && rm -rf /var/lib/apt/lists/*

# Put the Wine prefix at a fixed, HOME-agnostic path.  GitHub Actions sets HOME
# to /github/home or /root depending on the container user; using /opt/wine
# avoids any ambiguity.  Integration-test jobs inherit WINEPREFIX from this ENV
# so Wine always finds the pre-built prefix regardless of runner user.
ENV WINEPREFIX=/opt/wine
ENV DISPLAY=""
ENV WINEDLLOVERRIDES="winex11.drv="
ENV WINEDEBUG=-all
# UE4 / Unity dedicated-server binaries call SDL2 at startup even in headless
# mode.  Setting SDL_VIDEODRIVER=offscreen tells SDL2 to use a null video driver
# so the process doesn't crash trying to open an X11 display.  Wine/Proton are
# unaffected because their display path goes through winex11.drv / WINE vars.
ENV SDL_VIDEODRIVER=offscreen
ENV SDL_AUDIODRIVER=dummy

# Initialise the Wine prefix and install common Windows runtimes.
# wineserver --kill ensures the background wineserver exits cleanly before
# Docker commits the layer; || true keeps it non-fatal if none is running.
RUN wineboot --init \
 && winetricks -q win10 \
 && (winetricks -q --force vcrun2019 || true) \
 && (winetricks -q --force vcrun2022 || true) \
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

# Install Python test dependencies (pytest, pylint, coverage, etc.) so that
# integration-test runners can use them without a per-job pip install.
# --break-system-packages is required on Ubuntu 24.04 because the system Python
# is marked externally-managed (PEP 668).  This is safe in a throwaway CI image.
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# Create a non-root user so that game servers that refuse to start as root
# (e.g. Insurgency: Sandstorm, Mordhau, Squad, Palworld, Satisfactory, …) work
# correctly inside the CI container.  The integration-test runner switches to
# this user with `su - gsmuser` before launching pytest.
#
# uid 1001 matches the GitHub-hosted-runner `runner` user that owns the checked-
# out workspace volume, so the integration-test step does not need a separate
# `chown` pass over the repository tree.
#
# /opt/wine (the pre-built Wine prefix) is transferred to gsmuser so that Wine
# and Proton processes spawned by AlphaGSM under that account can write lock
# files and temporary state into the prefix without permission errors.
RUN useradd --create-home --shell /bin/bash --uid 1001 gsmuser \
 && chown -R gsmuser:gsmuser /opt/wine
