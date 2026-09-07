ARG WINE_PROTON_IMAGE=ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest
FROM ${WINE_PROTON_IMAGE}

# Prevent apt from asking questions
ARG DEBIAN_FRONTEND=noninteractive

# The integration image extends the same Wine/Proton runtime image that
# AlphaGSM launches for Docker-backed Windows servers. This lets Docker reuse
# those large layers on CI runners instead of storing a second Wine, prefix,
# Mono, and Proton stack beside large SteamCMD payloads.
#
# All system packages the integration tests need, baked into the image so each
# test runner starts ready to go without a per-job apt-get install.
#
#   screen                              — AlphaGSM's process supervisor
#   p7zip-full                          — .7z archive support
#   unzip bzip2 xz-utils                — archive formats used by some servers
#   libc++1                             — LLVM C++ runtime used by newer native
#                                         Linux dedicated servers such as Pavlov VR
#   libpulse-dev                         — PulseAudio development surface required
#                                         by Valheim on Linux
#   libcurl3t64-gnutls                  — GnuTLS-flavoured libcurl; Mordhau (and
#                                         similar CryEngine servers) link against
#                                         libcurl-gnutls.so.4 specifically
#                                         (Ubuntu 24.04 renamed this package from
#                                         libcurl3-gnutls to libcurl3t64-gnutls)
#   libstdc++5:i386                    — legacy 32-bit libstdc++.so.5 required by
#                                         the native Call of Duty dedicated server
#   jq                                 — required by the UT99 installer script
#   docker.io                          — Docker CLI used by Docker-backed
#                                         integration-test lanes inside the
#                                         integration container
#   gcc make                           — build tools used by q2server's source
#                                         compile path during integration
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        screen \
        p7zip-full \
        unzip bzip2 xz-utils \
        libc++1 \
        libpulse-dev \
        libcurl3t64-gnutls \
        libstdc++5:i386 \
        jq python3-pip python3-venv \
        docker.io \
        gcc make \
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

# ATLAS also still links against the OpenLDAP 2.4 runtime for liblber-2.4.so.2.
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends libgssapi3-heimdal libldap-common libsasl2-2 \
 && wget -q \
        "http://archive.ubuntu.com/ubuntu/pool/main/o/openldap/libldap-2.4-2_2.4.49+dfsg-2ubuntu1.10_amd64.deb" \
        -O /tmp/libldap-2.4-2.deb \
 && dpkg -i /tmp/libldap-2.4-2.deb \
 && rm -f /tmp/libldap-2.4-2.deb \
 && rm -rf /var/lib/apt/lists/*

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

# Install the .NET 6, 9, and 10 runtimes — required by Linux apphosts such as
# CryoFall (.NET 6), TShock (.NET 9), and SS14 (dotnet 10). Baking them into
# the integration image keeps them available under the non-root gsmuser account
# used by the integration-test job.
RUN wget -q \
       https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb \
       -O /tmp/packages-microsoft-prod.deb \
 && dpkg -i /tmp/packages-microsoft-prod.deb \
 && rm -f /tmp/packages-microsoft-prod.deb \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends dotnet-runtime-10.0 \
 && wget -q https://dot.net/v1/dotnet-install.sh -O /tmp/dotnet-install.sh \
 && bash /tmp/dotnet-install.sh --runtime dotnet --channel 6.0 --install-dir /usr/lib/dotnet \
 && bash /tmp/dotnet-install.sh --runtime dotnet --channel 9.0 --install-dir /usr/lib/dotnet \
 && rm -f /tmp/dotnet-install.sh \
 && rm -rf /var/lib/apt/lists/*

# UE4 / Unity dedicated-server binaries call SDL2 at startup even in headless
# mode.  Setting SDL_VIDEODRIVER=offscreen tells SDL2 to use a null video driver
# so the process doesn't crash trying to open an X11 display.  Wine/Proton are
# unaffected because their display path goes through winex11.drv / WINE vars.
ENV SDL_VIDEODRIVER=offscreen
ENV SDL_AUDIODRIVER=dummy

# Install Python test dependencies (pytest, pylint, coverage, etc.) so that
# integration-test runners can use them without a per-job pip install.
# --break-system-packages is required on Ubuntu 24.04 because the system Python
# is marked externally-managed (PEP 668).  This is safe in a throwaway CI image.
COPY requirements.txt requirements-runtime.txt /tmp/
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
# /opt/wine (the pre-built Wine prefix) and /opt/proton-ge (the baked Proton-GE
# tool tree) are transferred to gsmuser so Wine/Proton launches under that
# account can create their lock files and temporary state without permission
# errors.
RUN useradd --create-home --shell /bin/bash --uid 1001 gsmuser \
 && chown -R gsmuser:gsmuser /opt/wine /opt/proton-ge

# This is a generic CI tool image, not a game-runtime image.
WORKDIR /
ENTRYPOINT []
CMD ["bash"]
