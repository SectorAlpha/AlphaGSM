#!/usr/bin/env bash

set -Eeuo pipefail
set -x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-ubuntu:24.04}"

docker run --rm \
  -v "$REPO_ROOT:/src" \
  "$CONTAINER_IMAGE" \
  /bin/bash -lc '
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y python3 sudo git

mkdir -p /etc/sudoers.d

cd /src
bash ./scripts/install-system-wide.sh

test -f /etc/alphagsm.conf
test -d /home/alphagsm
test -d /home/alphagsm/gitlive
test -d /home/alphagsm/downloads
test -d /usr/local/lib/alphagsm
test -f /usr/local/lib/alphagsm/alphagsm
test -f /usr/local/lib/alphagsm/alphagsm-downloads
test -L /usr/local/bin/alphagsm
test "$(readlink -f /usr/local/bin/alphagsm)" = "/usr/local/lib/alphagsm/alphagsm"
test -x /usr/local/sbin/gitalphagsm
test -f /etc/sudoers.d/gameservers
grep -Fx "%alphagsm       ALL = (alphagsm) NOPASSWD:/usr/local/lib/alphagsm/alphagsm-downloads" /etc/sudoers.d/gameservers

python3 /usr/local/bin/alphagsm --help >/tmp/alphagsm-help.txt
test -s /tmp/alphagsm-help.txt
'
