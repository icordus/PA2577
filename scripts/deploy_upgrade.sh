#!/usr/bin/env bash
set -euo pipefail

# Upgrade the release and wait for readiness; Helm rolls back failed upgrades.
helm upgrade --install pa2577 helm/pa2577 \
  --namespace pa2577 \
  --wait --timeout 10m --atomic