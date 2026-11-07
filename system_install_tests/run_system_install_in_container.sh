#!/usr/bin/env bash

set -Eeuo pipefail
set -x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-ubuntu:24.04}"

docker run --rm \
  -v "$REPO_ROOT:/src:ro" \
  "$CONTAINER_IMAGE" \
  /bin/bash -lc '
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y python3 python3-pip python3-venv sudo git

# The installer reads the tree from a writable copy. A read-only mount keeps
# the test from changing the checkout.
mkdir -p /tmp/src
tar -C /src -cf - . | tar -C /tmp/src -xf -

python3 -m pip install --break-system-packages -r /tmp/src/requirements-runtime.txt

cd /tmp/src
bash ./scripts/install-system-wide.sh

test -f /etc/alphagsm.conf
grep -q "^user = alphagsm$" /etc/alphagsm.conf
grep -q "^db_path = /home/alphagsm/downloads/downloads.txt$" /etc/alphagsm.conf
grep -q "^target_path = /home/alphagsm/downloads/downloads$" /etc/alphagsm.conf
test -d /home/alphagsm/gitlive
test -d /home/alphagsm/downloads/downloads
test -d /usr/local/lib/alphagsm
test -f /usr/local/lib/alphagsm/alphagsm
test -f /usr/local/lib/alphagsm/alphagsm-downloads
test -L /usr/local/bin/alphagsm
test "$(readlink -f /usr/local/bin/alphagsm)" = "/usr/local/lib/alphagsm/alphagsm"
test -x /usr/local/sbin/gitalphagsm
test -f /etc/sudoers.d/gameservers
grep -Fx "%alphagsm ALL = (alphagsm) NOPASSWD:/usr/local/lib/alphagsm/alphagsm-downloads" /etc/sudoers.d/gameservers
visudo -cf /etc/sudoers.d/gameservers
test "$(stat -c %U /home/alphagsm/downloads)" = alphagsm

printf "\n# install-test-marker\n" >> /etc/alphagsm.conf
bash ./scripts/install-system-wide.sh
grep -q "install-test-marker" /etc/alphagsm.conf

python3 /usr/local/bin/alphagsm --help >/tmp/alphagsm-help.txt
test -s /tmp/alphagsm-help.txt
'
