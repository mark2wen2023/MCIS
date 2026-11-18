# Missing analysis scenario — developer check
Base94d5e38c926fda232bb987b60fa9145e4bcf01a7. Report sources.py emits analysis
scenario links; AnalysisPage passes scenario, but AnalysisView silently chose
BASELINE when the requested row was absent. Parent synthetic SSR failed
`missing scenario must be explicit`; fixed wrapper shows missing case/scenario
and allows explicit baseline selection, never automatic replacement. Valid view
is delegated unchanged to a child so hook order is stable across missing/valid.

From web:
./node_modules/.bin/esbuild tests/analysis-missing-scenario.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/mcis-analysis-missing.cjs
node /tmp/mcis-analysis-missing.cjs
npm run build

8 synthetic rendering/action assertions passed: no What-if data, absent row,
valid row, ordinary baseline and explicit callback. Constructed metadata/empty
series only, no public or real case fixtures, core/HTTP/model/browser. ECharts
canvas disabled. TypeScript/Vite passed766modules; >1500kB warning remains.
Approved dependencies reused, no install. Not browser/visual, historical version,
source verification or independent acceptance. No paused/refusal tests run.
