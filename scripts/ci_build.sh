#!/usr/bin/env bash
set -euo pipefail

# Build each application once; tests and publication use these exact image IDs.
docker build --platform linux/arm64 \
  --tag "$TASKS_BUILD_IMAGE" --file services/tasks/Dockerfile .
docker build --platform linux/arm64 \
  --tag "$STATISTICS_BUILD_IMAGE" --file services/statistics/Dockerfile .
{
  echo "TASKS_IMAGE_ID=$(docker image inspect --format '{{.Id}}' "$TASKS_BUILD_IMAGE")"
  echo "STATISTICS_IMAGE_ID=$(docker image inspect --format '{{.Id}}' "$STATISTICS_BUILD_IMAGE")"
} >> "$GITHUB_ENV"