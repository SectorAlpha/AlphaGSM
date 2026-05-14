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
      libc++1 \
        libsdl2-2.0-0 \
        libpulse0 \
       python3 \
       wget \
 && rm -rf /var/lib/apt/lists/*

# Older dedicated servers in the steamcmd-linux family still link against
# OpenSSL 1.1 or 1.0.x just like the CI integration image.
RUN wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb" \
       -O /tmp/libssl1.1.deb \
 && dpkg -i /tmp/libssl1.1.deb \
 && rm -f /tmp/libssl1.1.deb

RUN wget -q \
       "http://security.ubuntu.com/ubuntu/pool/main/o/openssl1.0/libssl1.0.0_1.0.2n-1ubuntu5_amd64.deb" \
       -O /tmp/libssl1.0.0.deb \
 && dpkg -i /tmp/libssl1.0.0.deb \
 && rm -f /tmp/libssl1.0.0.deb

# ATLAS still links against libprotobuf.so.10, so keep the legacy protobuf
# runtime available in the shared native SteamCMD Linux family image too.
RUN wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/p/protobuf/libprotobuf10_3.0.0-9.1ubuntu1_amd64.deb" \
       -O /tmp/libprotobuf10.deb \
 && dpkg -i /tmp/libprotobuf10.deb \
 && rm -f /tmp/libprotobuf10.deb

WORKDIR /srv/server

CMD ["/bin/bash"]