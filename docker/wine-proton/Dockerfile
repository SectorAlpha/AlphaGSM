FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        cabextract \
        curl \
        procps \
        unzip \
        wget \
        winbind \
        wine64 \
        wine32 \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/alphagsm-wine-proton-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-wine-proton-entrypoint \
    && mkdir -p /opt/proton /srv/server

WORKDIR /srv/server

ENTRYPOINT ["/usr/local/bin/alphagsm-wine-proton-entrypoint"]
CMD ["cmd.exe", "/c", "echo", "AlphaGSM wine-proton runtime ready"]
