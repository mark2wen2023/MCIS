#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/bowtie-preview-w153.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-bowtie-preview-w153.cjs --jsx=automatic --log-level=warning
node tests/.tmp-bowtie-preview-w153.cjs
