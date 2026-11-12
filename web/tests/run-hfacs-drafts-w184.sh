#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/hfacs-drafts-w184.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-hfacs-drafts-w184.cjs --jsx=automatic --log-level=warning
node tests/.tmp-hfacs-drafts-w184.cjs
