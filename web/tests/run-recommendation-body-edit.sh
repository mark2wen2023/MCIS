#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/recommendation-body-edit.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-recommendation-body-edit.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-recommendation-body-edit.cjs
