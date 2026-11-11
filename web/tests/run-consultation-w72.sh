#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/consultation-w72.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-consultation-w72.cjs --jsx=automatic --log-level=warning
node tests/.tmp-consultation-w72.cjs
