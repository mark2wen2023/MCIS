# Interview source lifecycle: synthetic verification

Base PR99 feat/interview-source-disclosure remote 3d783392e7f3187457d1d5bfba1e6efcbb6d9064 checked unchanged. Test-only independent branch; no product changes.

Reviewed new test before run: actual useContentLoad and SourceDisclosure compiled with synthetic hooks/JSX; deferred in-memory loaders, fetch throws. contentRequest is not called. Parent case/identity and record keys and response identity validation are checked as source text only. Keyed unmount/replacement and effect cleanup are explicitly simulated, not rendered by real React. No backend, Python, cases/seeds, media/model, browser, paused/refusal/write-probe tests.

Commands, web cwd:
```
node tests/interview-source-lifecycle.cjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```
4 scenarios pass: A unmounted/B resolves first then A late success; same with A ordinary late error; loaded A replaced by B with null source fields and no old link/hash; same record reload clears source before ordinary failure and does not restore it. Old instance writes counted after cleanup. Current synthetic output/link inspected. No denial path executed. No product defect established.

TypeScript/Vite passed; existing large-chunk warning retained. Existing dependency copy from /tmp/mcis-pr99-current/web/node_modules, no install or download. Not a clean-install, browser, real React scheduling, HTTP, production identity, backend isolation or full-suite/CI acceptance. No merge/deploy. Synthetic lifecycle assumptions must still be validated in supported real React/browser environment.
