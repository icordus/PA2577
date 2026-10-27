#!/usr/bin/env bash
set -euo pipefail

# Use disposable PostgreSQL and the exact application images built by this job.
docker pull --platform linux/arm64 "$POSTGRES_IMAGE"
python3 scripts/integration_http.py --execute \
  --run-id "$INTEGRATION_RUN_ID" \
  --tasks-image "$TASKS_IMAGE_ID" \
  --statistics-image "$STATISTICS_IMAGE_ID" \
  --postgres-image "$POSTGRES_IMAGE"