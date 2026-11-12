#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/case-metadata-w84.test.tsx --bundle --packages=external --platform=node --format=esm --outfile=tests/.tmp-case-metadata-w84.mjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-case-metadata-w84.mjs
