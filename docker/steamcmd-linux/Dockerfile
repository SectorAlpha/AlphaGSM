FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        lib32gcc-s1 \
      libstdc++5:i386 \
        lib32stdc++6 \
        libcurl3t64-gnutls \
        libatomic1 \
        libc++1 \
        libgdiplus \
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

RUN wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/libi/libidn/libidn11_1.33-2.2ubuntu2_amd64.deb" \
       -O /tmp/libidn11.deb \
 && dpkg -i /tmp/libidn11.deb \
 && rm -f /tmp/libidn11.deb

# Keep multiple supported dotnet runtimes available in the shared SteamCMD
# Linux family image for framework-dependent server entrypoints such as
# Bannerlord (.NET 6), TShock (.NET 9), and SS14 (.NET 10).
RUN wget -q \
       https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb \
       -O /tmp/packages-microsoft-prod.deb \
 && dpkg -i /tmp/packages-microsoft-prod.deb \
 && rm -f /tmp/packages-microsoft-prod.deb \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends dotnet-runtime-10.0 \
 && wget -q https://dot.net/v1/dotnet-install.sh -O /tmp/dotnet-install.sh \
 && bash /tmp/dotnet-install.sh --runtime dotnet --channel 9.0 --install-dir /usr/lib/dotnet \
 && bash /tmp/dotnet-install.sh --runtime dotnet --channel 6.0 --install-dir /usr/lib/dotnet \
 && rm -f /tmp/dotnet-install.sh \
 && rm -rf /var/lib/apt/lists/*

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends libgssapi3-heimdal libldap-common libsasl2-2 \
 && wget -q \
       "http://archive.ubuntu.com/ubuntu/pool/main/o/openldap/libldap-2.4-2_2.4.49+dfsg-2ubuntu1.10_amd64.deb" \
       -O /tmp/libldap-2.4-2.deb \
 && dpkg -i /tmp/libldap-2.4-2.deb \
 && rm -f /tmp/libldap-2.4-2.deb \
 && rm -rf /var/lib/apt/lists/*

RUN ln -sf /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so

WORKDIR /srv/server

CMD ["/bin/bash"]
