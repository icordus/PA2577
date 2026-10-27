#!/usr/bin/env bash
set -euo pipefail

# Report success only after publication and cleanup have both succeeded.
echo "CI passed for commit ${GITHUB_SHA}; use this SHA for deployment."