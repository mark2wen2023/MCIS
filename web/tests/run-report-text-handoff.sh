#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/report-text-handoff.test.tsx --bundle --platform=node --format=esm --packages=external --outfile=tests/.tmp-report-text-handoff.mjs --jsx=automatic --log-level=warning
node tests/.tmp-report-text-handoff.mjs
