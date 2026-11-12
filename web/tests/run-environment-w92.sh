#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/environment-w92.test.tsx --bundle --packages=external --platform=node --format=esm --outfile=tests/.tmp-environment-w92.mjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-environment-w92.mjs
