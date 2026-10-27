#!/usr/bin/env bash
set -euo pipefail

# Validate the selected chart and cluster, then export deploy settings.
image_tag="$(sed -n 's/^imageTag: "\([^\"]*\)"$/\1/p' helm/pa2577/values.yaml)"
if [[ ! "$image_tag" =~ ^(v[0-9]+\.[0-9]+\.[0-9]+|[0-9a-f]{40})$ ]]; then
  echo '::error::Invalid Helm imageTag; expected vMAJOR.MINOR.PATCH or a full commit SHA.'
  exit 1
fi

actual_context="$(kubectl config current-context)"
if [[ "$actual_context" != "${EXPECTED_KUBE_CONTEXT:?}" ]]; then
  echo "::error::Unexpected Kubernetes context: $actual_context" >&2
  exit 1
fi

kubectl wait --for=condition=Ready node/raspberrypi2 --timeout=30s >/dev/null
node_arch="$(kubectl get node raspberrypi2 -o jsonpath='{.metadata.labels.kubernetes\.io/arch}')"
[[ "$node_arch" == "arm64" ]]
[[ "$(kubectl get namespace pa2577 -o jsonpath='{.status.phase}')" == "Active" ]]
[[ "$(kubectl -n pa2577 get pvc pa2577-postgres-data -o jsonpath='{.status.phase}')" == "Bound" ]]
[[ "$(kubectl -n pa2577 get pvc pa2577-postgres-data -o jsonpath='{.spec.volumeName}')" == "pa2577-postgres-pv" ]]
kubectl -n pa2577 get secret pa2577-database -o name >/dev/null
helm status pa2577 --namespace pa2577 >/dev/null

kube_version="$(kubectl version -o jsonpath='{.serverVersion.gitVersion}')"
helm lint helm/pa2577 --namespace pa2577 --kube-version "${kube_version#v}" --strict
helm template pa2577 helm/pa2577 --namespace pa2577 --kube-version "${kube_version#v}" >/dev/null

node_ip="$(kubectl get node raspberrypi2 -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')"
node_port="$(kubectl -n pa2577 get service pa2577-tasks -o jsonpath='{.spec.ports[0].nodePort}')"
[[ -n "$node_ip" && "$node_port" =~ ^[0-9]+$ ]]
[[ "$node_port" -ge 30000 && "$node_port" -le 32767 ]]

printf 'DEPLOY_IMAGE_TAG=%s\nDEPLOY_BASE_URL=http://%s:%s\n' \
  "$image_tag" "$node_ip" "$node_port" >> "${GITHUB_ENV:?}"
