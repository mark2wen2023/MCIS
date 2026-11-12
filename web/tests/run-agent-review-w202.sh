#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/agent-review-w202.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-agent-review-w202.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-agent-review-w202.cjs
