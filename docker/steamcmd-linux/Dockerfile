FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        lib32gcc-s1 \
        lib32stdc++6 \
        libcurl3t64-gnutls \
        libatomic1 \
        libsdl2-2.0-0 \
        libpulse0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/server

CMD ["/bin/bash"]