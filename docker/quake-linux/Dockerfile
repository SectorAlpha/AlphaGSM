FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        lib32gcc-s1 \
        lib32stdc++6 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/server

CMD ["/bin/bash"]