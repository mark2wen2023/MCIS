#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -x node_modules/.bin/esbuild ]] || { echo 'Existing offline esbuild required' >&2; exit 1; }
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
./node_modules/.bin/esbuild tests/bowtie-svg-status.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile="$out/check.cjs" --log-level=warning
node "$out/check.cjs"
