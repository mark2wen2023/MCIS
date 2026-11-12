#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/knowledge-w191.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-knowledge-w191.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-knowledge-w191.cjs
