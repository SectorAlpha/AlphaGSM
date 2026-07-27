FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEPREFIX=/opt/wine
ENV DISPLAY=""
ENV WINEDLLOVERRIDES="winex11.drv="
ENV WINEDEBUG=-all
ENV SDL_VIDEODRIVER=offscreen
ENV SDL_AUDIODRIVER=dummy

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        cabextract \
        curl \
        fontconfig \
        lib32gcc-s1 \
        lib32stdc++6 \
        libatomic1 \
        libgdiplus \
        libsdl2-2.0-0 \
        libcurl4-gnutls-dev \
        libcurl3t64-gnutls:i386 \
        libcurl4-gnutls-dev:i386 \
        libpulse0 \
        python3 \
        procps \
        unzip \
        wget \
        winbind \
        winetricks \
        wine64 \
        wine32:i386 \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN wineboot --init \
    && winetricks -q win10 \
    && (winetricks -q --force corefonts || true) \
    && (winetricks -q --force vcrun2019 || true) \
    && (winetricks -q --force vcrun2022 || true) \
    && (wineserver --kill || true) \
    && rm -rf /tmp/wine-*

RUN wget -q \
        "https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi" \
        -O /tmp/wine-mono.msi \
    && wine msiexec /i /tmp/wine-mono.msi /qn \
    && (wineserver --kill || true) \
    && rm -f /tmp/wine-mono.msi \
    && rm -rf /tmp/wine-*

COPY scripts/install_proton.sh /tmp/install_proton.sh
COPY scripts/select_proton_asset.py /tmp/select_proton_asset.py
RUN GITHUB_TOKEN=${GITHUB_TOKEN:-} \
    PROTON_GE_DIR=/opt/proton-ge \
    bash /tmp/install_proton.sh proton \
    && ln -s /opt/proton-ge /opt/proton \
    && rm -f /tmp/install_proton.sh /tmp/select_proton_asset.py

COPY docker/wine-proton/entrypoint.sh /usr/local/bin/alphagsm-wine-proton-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-wine-proton-entrypoint \
    && mkdir -p /srv/server \
    && chown -R root:root /opt/proton-ge /opt/proton /opt/wine

WORKDIR /srv/server

ENTRYPOINT ["/usr/local/bin/alphagsm-wine-proton-entrypoint"]
CMD ["cmd.exe", "/c", "echo", "AlphaGSM wine-proton runtime ready"]
