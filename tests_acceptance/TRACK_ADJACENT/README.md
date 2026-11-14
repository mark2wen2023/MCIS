# Selected returned-track predecessor display

One production file changes: web/src/tracks/TrackView.tsx. The selected point detail compares against the immediately preceding record of the unfiltered returned array, not the source-filtered display. Shows both UTC values and recorded provenance/source, original returned position, and signed timeSec difference. First returned point has unknown outside-window predecessor; duplicate and reversed times remain explicit. No sorting, interpolation, missing-data threshold, genuine-AIS claim or backend/COLREG change.

Based on real main 3aba2bf03e393909c611489ae573a887087637ac. All 34 currently open PR file lists inspected; none changes TrackView.tsx. This does not certify unknown unpublished local changes. Independent review in INDEPENDENT.md.

From repository root with installed web dependencies:
```
NODE_PATH=$PWD/web/node_modules web/node_modules/.bin/esbuild tests_acceptance/TRACK_ADJACENT/detail.test.tsx --bundle --platform=node --jsx=automatic --outfile=/tmp/mcis-track-detail.cjs
node /tmp/mcis-track-detail.cjs
NODE_PATH=$PWD/web/node_modules web/node_modules/.bin/esbuild tests_acceptance/TRACK_ADJACENT/independent.test.tsx --bundle --platform=node --jsx=automatic --format=esm --outfile=/tmp/mcis-track-independent.mjs
MCIS_HAPPY_DOM=/absolute/path/to/installed/happy-dom/lib/index.js node /tmp/mcis-track-independent.mjs
```
HappyDOM is an explicitly supplied test-only dependency, not installed by this change. SSR and independently mounted component tests use synthetic tracks only. Full tsc -b / Vite build passed with existing large-chunk warning. Not real-browser visual/accessibility, real AIS, trusted identity or API end-to-end acceptance. No deployment/merge.
