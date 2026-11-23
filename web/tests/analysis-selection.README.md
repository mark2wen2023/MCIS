# Analysis native selection — synthetic regression

Parent main: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Actual AnalysisView case and series selectors now use AnalysisChoice native
buttons with aria-pressed and the original callbacks. Scoped CSS preserves the
segmented layout and provides an inset focus outline. No formula, fetch, route,
default selection or authorization changes; no seed files are read by this test.

From web/, using existing offline dependencies:

```sh
./node_modules/.bin/esbuild tests/analysis-selection.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --loader:.css=empty --outfile=/tmp/mcis-analysis-selection.cjs --log-level=warning
node /tmp/mcis-analysis-selection.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

22 assertions passed: actual production button type/pressed state/escaped text,
single direct callback, no duplicate key handler, actual AnalysisView SSR of case
and baseline/scenario selection, and null-versus-zero curve/formatting checks.
Fixtures are hand-made synthetic props, not backend results. Callback tests invoke
the React element handler directly; SSR does not run effects, ECharts or keyboard.
TypeScript and Vite passed (existing bundle-size warning).

Real Tab/Enter/Space activation, focus appearance and pixel/layout checks remain
pending a qualified sandboxed browser. The old analysis-w12 test reads seed and
historical datasets and was deliberately not run in this synthetic-only scope.
No service, browser, ingestion, report, archive, merge or deployment performed.
