FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
       docker-cli \
        docker.io \
        git \
        wget \
 && test -x /usr/bin/docker \
 && rm -rf /var/lib/apt/lists/*

RUN wget -q -O /usr/share/keyrings/adoptium.asc \
        https://packages.adoptium.net/artifactory/api/gpg/key/public \
 && . /etc/os-release \
 && printf 'deb [arch=%s signed-by=/usr/share/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb %s main\n' \
        "$(dpkg --print-architecture)" \
        "$VERSION_CODENAME" \
        > /etc/apt/sources.list.d/adoptium.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends temurin-25-jre \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/alphagsm

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/manager/entrypoint.sh /usr/local/bin/alphagsm-manager-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-manager-entrypoint \
 && mkdir -p /srv/alphagsm/home /srv/alphagsm/servers

ENV PYTHONPATH=/opt/alphagsm/src
ENV ALPHAGSM_CONFIG_LOCATION=/srv/alphagsm/alphagsm.conf
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ENTRYPOINT ["/usr/local/bin/alphagsm-manager-entrypoint"]
CMD ["sleep", "infinity"]