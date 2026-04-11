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
        lib32gcc-s1 \
        lib32stdc++6 \
        libatomic1 \
        libsdl2-2.0-0 \
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
    && (winetricks -q --force vcrun2019 || true) \
    && (winetricks -q --force vcrun2022 || true) \
    && (wineserver --kill || true)

RUN wget -q \
        "https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi" \
        -O /tmp/wine-mono.msi \
    && wine msiexec /i /tmp/wine-mono.msi /qn \
    && (wineserver --kill || true) \
    && rm -f /tmp/wine-mono.msi

COPY scripts/install_proton.sh /tmp/install_proton.sh
RUN GITHUB_TOKEN=${GITHUB_TOKEN:-} \
    PROTON_GE_DIR=/opt/proton-ge \
    bash /tmp/install_proton.sh proton \
    && ln -s /opt/proton-ge /opt/proton \
    && rm -f /tmp/install_proton.sh

COPY docker/wine-proton/entrypoint.sh /usr/local/bin/alphagsm-wine-proton-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-wine-proton-entrypoint \
    && mkdir -p /srv/server \
    && chown -R root:root /opt/proton-ge /opt/proton /opt/wine

WORKDIR /srv/server

ENTRYPOINT ["/usr/local/bin/alphagsm-wine-proton-entrypoint"]
CMD ["cmd.exe", "/c", "echo", "AlphaGSM wine-proton runtime ready"]
