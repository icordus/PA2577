#!/usr/bin/env bash
set -euo pipefail

# Pass the token through stdin, never through command arguments or logs.
if [[ -z "$DOCKERHUB_TOKEN" ]]; then
  echo 'DOCKERHUB_TOKEN is required for publication.' >&2
  exit 1
fi
printf '%s' "$DOCKERHUB_TOKEN" | docker login docker.io \
  --username "$DOCKERHUB_USERNAME" --password-stdin