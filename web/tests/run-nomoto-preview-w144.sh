#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/nomoto-preview-w144.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-nomoto-preview-w144.cjs --jsx=automatic --log-level=warning
node tests/.tmp-nomoto-preview-w144.cjs
