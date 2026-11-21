#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -x node_modules/.bin/esbuild ]] || { echo 'Missing existing offline esbuild dependency' >&2; exit 2; }
output=$(mktemp /tmp/mcis-bowtie-paths-XXXXXX.cjs)
trap 'rm -f "$output"' EXIT
node_modules/.bin/esbuild tests/bowtie-unprotected-paths.test.tsx --bundle --platform=node --format=cjs --outfile="$output" --jsx=automatic --log-level=warning
node "$output"
