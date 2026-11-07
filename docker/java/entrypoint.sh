#!/usr/bin/env bash
set -euo pipefail

JAVA_MAJOR="${ALPHAGSM_JAVA_MAJOR:-17}"

case "$JAVA_MAJOR" in
  17) export JAVA_HOME=/usr/lib/jvm/temurin-17-jre-amd64 ;;
  21) export JAVA_HOME=/usr/lib/jvm/temurin-21-jre-amd64 ;;
  25) export JAVA_HOME=/usr/lib/jvm/temurin-25-jre-amd64 ;;
  *)
    echo "Unsupported ALPHAGSM_JAVA_MAJOR: $JAVA_MAJOR" >&2
    exit 2
    ;;
esac

export PATH="$JAVA_HOME/bin:$PATH"

exec "$@"
