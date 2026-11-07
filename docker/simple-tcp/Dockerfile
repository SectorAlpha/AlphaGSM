FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
      mumble-server \
       python3 \
 && ln -s /usr/sbin/murmurd /usr/local/bin/mumble-server \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/server

CMD ["/bin/bash"]
