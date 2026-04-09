FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
       default-jre-headless \
        docker.io \
        git \
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

ENTRYPOINT ["/usr/local/bin/alphagsm-manager-entrypoint"]
CMD ["sleep", "infinity"]