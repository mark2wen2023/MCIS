#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -x node_modules/.bin/esbuild ]] || { echo 'Missing existing offline esbuild' >&2; exit 2; }
output=$(mktemp /tmp/mcis-ecfc-node-review-XXXXXX.cjs)
trap 'rm -f "$output"' EXIT
for test in tests/ecfc-node-review.test.tsx tests/ecfc-model.test.tsx; do
 node_modules/.bin/esbuild "$test" --bundle --platform=node --format=cjs --outfile="$output" --jsx=automatic --log-level=warning
 node "$output"
done
