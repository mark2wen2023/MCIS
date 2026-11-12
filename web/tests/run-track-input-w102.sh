#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/track-input-w102.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-track-input-w102.cjs --jsx=automatic --log-level=warning
node tests/.tmp-track-input-w102.cjs
