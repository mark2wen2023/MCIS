#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/align-preview-w41.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-align-preview-w41.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-align-preview-w41.cjs
