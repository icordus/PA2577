#!/usr/bin/env bash
set -euo pipefail

# Reject invalid release settings before creating temporary resources.
if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo '::error::GITHUB_SHA is not a full 40-character commit SHA.'
  exit 1
fi
if [[ ! "${IMAGE_VERSION:-}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo '::error::IMAGE_VERSION must be a fixed vMAJOR.MINOR.PATCH value, such as v0.1.0.'
  exit 1
fi
if [[ -z "${DOCKERHUB_USERNAME:-}" ]]; then
  echo '::error::Set the repository variable DOCKERHUB_USERNAME.'
  exit 1
fi
if [[ ! "$DOCKERHUB_USERNAME" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
  echo '::error::DOCKERHUB_USERNAME has an invalid format.'
  exit 1
fi

# Require the same ARM64 platform for the runner and Docker daemon.
case "$(uname -m)" in
  aarch64|arm64) ;;
  *) echo '::error::The self-hosted runner must be Linux ARM64.' >&2; exit 1 ;;
esac
case "$(docker info --format '{{.OSType}}/{{.Architecture}}')" in
  linux/aarch64|linux/arm64) ;;
  *) echo 'A reachable Linux ARM64 Docker daemon is required.' >&2; exit 1 ;;
esac
if ! command -v python3 >/dev/null 2>&1; then
  echo '::error::python3 is required on the self-hosted runner.'
  exit 1
fi

# Keep credentials in a private job directory and share its path with later steps.
umask 077
DOCKER_CONFIG="$(mktemp -d "$RUNNER_TEMP/pa2577-docker-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT-XXXXXX")"
export DOCKER_CONFIG
printf 'DOCKER_CONFIG=%s\n' "$DOCKER_CONFIG" >> "$GITHUB_ENV"
chmod 700 "$DOCKER_CONFIG"
python3 scripts/ci_run_id.py