FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        docker-cli \
        docker.io \
        git \
        lib32gcc-s1 \
        lib32stdc++6 \
        util-linux \
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

COPY requirements.txt requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY . .
COPY docker/manager/entrypoint.sh /usr/local/bin/alphagsm-manager-entrypoint

RUN chmod +x /usr/local/bin/alphagsm-manager-entrypoint \
 && groupadd --gid 1000 alphagsm \
 && useradd --uid 1000 --gid 1000 --home-dir /home/alphagsm --create-home \
        --shell /bin/bash alphagsm \
 && install -d -o 1000 -g 1000 \
        /srv/alphagsm \
        /srv/alphagsm/home \
        /srv/alphagsm/servers

ENV PYTHONPATH=/opt/alphagsm/src
ENV ALPHAGSM_CONFIG_LOCATION=/srv/alphagsm/alphagsm.conf
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ENTRYPOINT ["/usr/local/bin/alphagsm-manager-entrypoint"]
CMD ["sleep", "infinity"]
