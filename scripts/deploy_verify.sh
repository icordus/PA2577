#!/usr/bin/env bash
set -euo pipefail

# Check rollout, image tags, storage, and read-only HTTP endpoints.
for deployment in pa2577-tasks pa2577-statistics pa2577-postgres; do
  kubectl -n pa2577 rollout status "deployment/$deployment" --timeout=180s
done

tasks_image="$(kubectl -n pa2577 get deployment pa2577-tasks -o jsonpath='{.spec.template.spec.containers[0].image}')"
statistics_image="$(kubectl -n pa2577 get deployment pa2577-statistics -o jsonpath='{.spec.template.spec.containers[0].image}')"
[[ "$tasks_image" == "docker.io/icordus/pa2577-tasks:${DEPLOY_IMAGE_TAG:?}" ]]
[[ "$statistics_image" == "docker.io/icordus/pa2577-statistics:${DEPLOY_IMAGE_TAG:?}" ]]
[[ "$(kubectl -n pa2577 get pvc pa2577-postgres-data -o jsonpath='{.status.phase}')" == "Bound" ]]

python3 scripts/verify_deployment_http.py --base-url "${DEPLOY_BASE_URL:?}"
echo "Deployed Helm chart version $DEPLOY_IMAGE_TAG from main."