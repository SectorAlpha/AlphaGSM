FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
       python3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/server

CMD ["/bin/bash"]
