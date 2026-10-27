#!/usr/bin/env bash
set -euo pipefail

# Show the operator's rollback command without changing the cluster.
echo 'Inspect helm history pa2577 -n pa2577, then run helm rollback pa2577 <previous-revision> -n pa2577 --wait.'
echo 'No automatic rollback is performed after HTTP verification failures.'
