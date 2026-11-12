#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/interview-context.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-interview-context.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-interview-context.cjs
