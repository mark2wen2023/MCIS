# W17 EvidencePage browser gate (authored, browser NOT RUN)

Product parent: 29fefb4c3789f248c4af29a72f59f0e213ecd107.
Harness source: 17f24befc9a45dffe597d2ce298130f1c22dda08.
Only this test directory is added; product files remain byte-identical to parent.
This fixture imports the actual EvidencePage, API wrapper, hooks, metrics and charts.
It does not reproduce the page or modify product code. MemoryRouter controls two
synthetic cases. A controlled fetch returns only hand-built synthetic lists or
403 responses; the original lifecycle mode keeps ancillary requests unavailable.
The added conflict mode supplies a synthetic case and one event, empty tracks
(no CPA calculation), and a separately pending conflict request.
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
The conflict mode checks one synthetic timeline event remains in the mounted
ECharts option alongside available evidence. It does not validate CPA values.

receipt.json has schema mcis-evidence-page-browser-1, passed (false until all
checks finish), actual browserVersion, exact built asset SHA-256 map, and checks
(width, touch, late or conflicts, passed). A failing run must never be treated as passing;
process exit and passed=true are both required. Screenshots show successful empty
states and final conflict states. Do not commit output, compiled Python or generated dist.

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

## Combined conflict gate (browser pending)

The same command also runs same-case initial pending → denied / successful empty
/ successful empty again / nonempty. Each is a fresh mount of SYN-A, not a claimed
same-mount refresh. Evidence and timeline succeed before conflicts settle, and
must remain afterward. No product refresh/write control is introduced.
The nonempty table includes an unknown-time conflict and a zero-time conflict;
actual chart options must include only the latter marker. Generic unavailability
must not be an empty table. All network outside intercepted fixture assets fails;
all unexpected fetches fail. Two viewport widths remain non-touch.

Available local checks: inherited 13 JS predicate checks, conflict SSR 16,
evidence metric SSR 10, Python syntax and Vite fixture build. They are NOT mounted
browser passes. Known blocked Chromium was not retried. No screenshots/receipt
from a real browser were produced here. Use a qualified normal sandbox host with
existing dependencies for the one check.py command above. Require exit 0 AND
receipt passed=true AND externalRequests=0; inspect the per-width conflict checks.

## Explicit fixture endpoint boundary

`request-policy.mjs` is shared by the fixture and 37 offline positive/negative
checks. Only GET on the exact case root, evidence list, custody chain verify,
timeline, conflicts, tracks, access-policy and EV-001 custody for SYN-A/B is
allowed. All other URLs (including unknown same-case URLs, query variants,
other evidence IDs and writes) record `unexpected` and return 403. Allowed
ancillary failures remain intentional; no request falls through to the network.

```sh
node web/tests/evidence-page-browser/request-policy.test.mjs
```

Before resolving each conflict request, the real-browser script now requires
exactly two pending notices (table and chart) and zero chart markLines, after
confirming the existing event is rendered. Those browser assertions remain
UNRUN here; offline policy tests, predicate tests, Python syntax and fixture
build are the executed checks, not browser acceptance.
