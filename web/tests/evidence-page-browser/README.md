# W17 EvidencePage browser gate (authored, browser NOT RUN)

Product parent: de19e7ab4ee7c5e9fa861ed40a64ac7c0e348151.
This fixture imports the actual EvidencePage, API wrapper, hooks, metrics and charts.
It does not reproduce the page or modify product code. MemoryRouter controls two
synthetic cases. A controlled fetch returns only hand-built synthetic lists or
403 responses; ancillary page requests deliberately receive unavailable responses.
No model, backend, data seed, archive, original file or business write is involved.
The identity button changes the existing local simulated role; not a real login
or a proof of production permissions. Pending callbacks are test controls only.

Using existing web dependencies from repository root:

```sh
./web/node_modules/.bin/vite build --config web/tests/evidence-page-browser/vite.config.ts
python -m py_compile web/tests/evidence-page-browser/check.py
```

On an eligible host with already-installed Playwright and normal sandbox-capable
Chromium, explicitly run (replace paths; output must not exist):

```sh
python web/tests/evidence-page-browser/check.py \
  --chromium /absolute/path/to/chromium \
  --dist "$PWD/.evidence-page-browser-dist" \
  --output /absolute/new/output-directory
```

No server is started. Playwright serves only built assets by intercepting the
reserved https://mcis-synthetic.invalid origin; other requests are blocked and
fail acceptance. Chromium sandbox is explicitly enabled; no unsafe launch flags.
Missing dependencies or launch failures are nonzero; do not install or bypass
sandbox merely to run this command. No legacy browser runner is invoked.

Planned checks at 1440 and 390 pixels (both mouse/non-touch): initial metrics,
A result visible then case switch clears it, old case success and failure cannot
replace current B, identity change invalidates pending old responses, current
403 shows unavailable rather than empty, successful empty list shows actual zero.
This is not keyboard, layout approval, real authorization, server audit or E2E.
Ancillary charts/timeline are not data-validated by this fixture.

receipt.json has schema mcis-evidence-page-browser-1, passed (false until all
checks finish), actual browserVersion, exact built asset SHA-256 map, and checks
(width, touch, late, passed). A failing run must never be treated as passing;
process exit and passed=true are both required. Screenshots show successful empty
states only. Do not commit output, compiled Python or generated dist.

Local authoring checks: Vite build exit0 (large chunk warning), Python compile
exit0, inherited evidence-metrics SSR 10 assertions exit0. Browser not attempted
on the known sandbox-blocked host; no mounted lifecycle assertions yet passed.

## Request/metric wait correction

Every navigation/identity action captures the monotonic request baseline BEFORE
clicking. The wait uses one uniquely matching new request (`id > baseline`, exact
case evidence URL and encoded simulated operator). Old pending entries and
ambiguous matches cannot satisfy it. Initial full navigation uses baseline zero.
Metric waits require exactly four selected metric values, never empty-array truth.
Old rejected responses carry LATE-* markers; current rejection carries
CURRENT-DENIAL, which must remain visible after the old request completes.

```sh
node web/tests/evidence-page-browser/predicates.test.cjs
```

13 ordinary offline checks execute the same JS predicates loaded by check.py,
including old pending, wrong case/operator, ambiguous requests and 0/3/5 metrics.
These checks passed; they do not run Playwright, React lifecycle or Chromium.
The corrected fixture also builds and check.py compiles; browser remains unrun.
