#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/consultation-w7.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-consultation-w7.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-consultation-w7.cjs
