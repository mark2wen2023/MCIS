#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/evidence-intake-w42.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-evidence-intake-w42.cjs --jsx=automatic --log-level=warning
node tests/.tmp-evidence-intake-w42.cjs
