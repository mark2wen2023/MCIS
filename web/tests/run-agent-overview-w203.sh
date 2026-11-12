#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/agent-overview-w203.test.ts --bundle --platform=node --format=cjs --outfile=tests/.tmp-agent-overview-w203.cjs --log-level=warning
node tests/.tmp-agent-overview-w203.cjs
