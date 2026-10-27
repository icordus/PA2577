#!/usr/bin/env bash
set -euo pipefail

tasks_repo="docker.io/$DOCKERHUB_USERNAME/pa2577-tasks"
statistics_repo="docker.io/$DOCKERHUB_USERNAME/pa2577-statistics"
tasks_sha_image="$tasks_repo:$GITHUB_SHA"
statistics_sha_image="$statistics_repo:$GITHUB_SHA"
tasks_version_image="$tasks_repo:$IMAGE_VERSION"
statistics_version_image="$statistics_repo:$IMAGE_VERSION"

# Refuse existing release tags or an inconclusive registry response.
for image in "$tasks_version_image" "$statistics_version_image"; do
  set +e
  inspect_output=$(docker manifest inspect "$image" 2>&1)
  inspect_status=$?
  set -e
  if [[ "$inspect_status" -eq 0 ]]; then
    echo "::error::Release image tag already exists: $image"
    exit 1
  fi
  if [[ "$inspect_output" != *"manifest unknown"* && "$inspect_output" != *"no such manifest"* ]]; then
    echo '::error::Could not safely verify that the release image tag is unused; refusing to publish.'
    exit 1
  fi
done

# Both version and SHA tags must refer to the tested image IDs.
docker tag "$TASKS_IMAGE_ID" "$tasks_sha_image"
docker tag "$STATISTICS_IMAGE_ID" "$statistics_sha_image"
docker tag "$TASKS_IMAGE_ID" "$tasks_version_image"
docker tag "$STATISTICS_IMAGE_ID" "$statistics_version_image"
for image in "$tasks_sha_image" "$tasks_version_image"; do
  [[ "$(docker image inspect --format '{{.Id}}' "$image")" == "$TASKS_IMAGE_ID" ]]
done
for image in "$statistics_sha_image" "$statistics_version_image"; do
  [[ "$(docker image inspect --format '{{.Id}}' "$image")" == "$STATISTICS_IMAGE_ID" ]]
done

docker push "$tasks_sha_image"
docker push "$statistics_sha_image"
docker push "$tasks_version_image"
docker push "$statistics_version_image"

# Record the published references in the Actions summary.
{
  printf '## Tested Images\n\nCommit: `%s`\nVersion: `%s`\n\n' "$GITHUB_SHA" "$IMAGE_VERSION"
  printf -- '- `%s`\n- `%s`\n- `%s`\n- `%s`\n' \
    "$tasks_sha_image" "$statistics_sha_image" \
    "$tasks_version_image" "$statistics_version_image"
} >> "$GITHUB_STEP_SUMMARY"