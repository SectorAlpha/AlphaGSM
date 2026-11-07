#!/usr/bin/env bash
set -euo pipefail

config_location="${ALPHAGSM_CONFIG_LOCATION:-/srv/alphagsm/alphagsm.conf}"
if [[ -n "${ALPHAGSM_HOME:-}" ]]; then
  shared_root="$ALPHAGSM_HOME"
else
  shared_root="$(dirname -- "$config_location")"
fi

effective_uid="$(id -u)"
effective_gid="$(id -g)"
expected_uid="${ALPHAGSM_HOST_UID:-}"
expected_gid="${ALPHAGSM_HOST_GID:-}"

if [[ "$effective_uid" == "0" ]]; then
  identity_source="$config_location"
  if [[ ! -e "$identity_source" ]]; then
    identity_source="$shared_root"
  fi
  expected_uid="${expected_uid:-$(stat -c '%u' "$identity_source")}"
  expected_gid="${expected_gid:-$(stat -c '%g' "$identity_source")}"
  docker_gid="${ALPHAGSM_DOCKER_GID:-}"
  if [[ -z "$docker_gid" && -e /var/run/docker.sock ]]; then
    docker_gid="$(stat -c '%g' /var/run/docker.sock)"
  fi
  docker_gid="${docker_gid:-$expected_gid}"

  if [[ ! "$expected_uid" =~ ^[0-9]+$ || "$expected_uid" == "0" ]]; then
    echo "AlphaGSM manager refuses to continue with effective UID 0." >&2
    exit 1
  fi
  if [[ ! "$expected_gid" =~ ^[0-9]+$ || ! "$docker_gid" =~ ^[0-9]+$ ]]; then
    echo "AlphaGSM manager requires numeric host and Docker group IDs." >&2
    exit 1
  fi

  export ALPHAGSM_HOST_UID="$expected_uid"
  export ALPHAGSM_HOST_GID="$expected_gid"
  export ALPHAGSM_DOCKER_GID="$docker_gid"
  exec setpriv \
    --reuid "$expected_uid" \
    --regid "$expected_gid" \
    --groups "$docker_gid" \
    -- "$0" "$@"
fi

expected_uid="${expected_uid:-$effective_uid}"
expected_gid="${expected_gid:-$effective_gid}"

if [[ "$effective_uid" == "0" ]]; then
  echo "AlphaGSM manager refuses to run with effective UID 0." >&2
  exit 1
fi
if [[ "$effective_uid" != "$expected_uid" || "$effective_gid" != "$expected_gid" ]]; then
  echo "AlphaGSM manager identity does not match the requested host UID:GID." >&2
  exit 1
fi

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
