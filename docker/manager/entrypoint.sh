#!/usr/bin/env bash
set -euo pipefail

shared_root="${ALPHAGSM_HOME:-/srv/alphagsm}"
export ALPHAGSM_HOME="$shared_root"
export HOME="$shared_root"

mkdir -p \
  "$shared_root/home/conf" \
  "$shared_root/home/downloads/downloads" \
  "$shared_root/home/logs" \
  "$shared_root/servers"

if [[ -n "${GHCR_USERNAME:-}" && -n "${GHCR_TOKEN:-}" ]]; then
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
fi

if [[ "${ALPHAGSM_PULL_RUNTIME_IMAGES:-1}" == "1" ]]; then
  mapfile -t runtime_images < <(
    python - <<'PY'
from server.runtime import RUNTIME_FAMILY_DEFAULTS

seen = []
for metadata in RUNTIME_FAMILY_DEFAULTS.values():
    image = metadata.get("image")
    if image and image not in seen:
        seen.append(image)
for image in seen:
    print(image)
PY
  )

  for image in "${runtime_images[@]}"; do
    docker pull "$image"
  done
fi

exec "$@"