#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/package-w83.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-package-w83.cjs --jsx=automatic --log-level=warning
node tests/.tmp-package-w83.cjs
