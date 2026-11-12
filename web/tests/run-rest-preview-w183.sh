#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/rest-preview-w183.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-rest-preview-w183.cjs --jsx=automatic --log-level=warning
node tests/.tmp-rest-preview-w183.cjs
