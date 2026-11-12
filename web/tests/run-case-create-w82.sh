#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/case-create-w82.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-case-create-w82.cjs --jsx=automatic --log-level=warning
node tests/.tmp-case-create-w82.cjs
