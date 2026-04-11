FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
 && rm -rf /var/lib/apt/lists/*

RUN wget -q -O /usr/share/keyrings/adoptium.asc \
        https://packages.adoptium.net/artifactory/api/gpg/key/public \
 && printf 'deb [arch=%s signed-by=/usr/share/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb %s main\n' \
        "$(dpkg --print-architecture)" \
        "$(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release)" \
        > /etc/apt/sources.list.d/adoptium.list \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
        bash \
        python3 \
        temurin-17-jre \
        temurin-21-jre \
        temurin-25-jre \
 && rm -rf /var/lib/apt/lists/*

COPY docker/java/entrypoint.sh /usr/local/bin/alphagsm-java-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-java-entrypoint \
 && mkdir -p /srv/server

WORKDIR /srv/server

ENTRYPOINT ["/usr/local/bin/alphagsm-java-entrypoint"]
CMD ["sh", "-lc", "exec java -jar \"${ALPHAGSM_SERVER_JAR:-server.jar}\" nogui"]
