# Registered preview real-network transport acceptance

This is **not browser or visual acceptance**. It uses the actual frontend `registeredBody`, `intakeRequest`, and `registeredResult` code in Node. The only fetch adapter resolves relative URLs against a dynamic `http://127.0.0.1:<port>` supplied by the runner; native fetch supplies every response. No response fixtures or core doubles are used.

The Python runner creates a disposable seeded SQLite/data directory, starts real uvicorn on a dynamic loopback port and the existing Vite dev proxy on a dynamic free loopback port in the same process tree. It requires installed service dependencies, existing web dependencies (Vite/esbuild), Node with native fetch, and an actually compiled compatible W2 wrapper. It fails rather than falling back to a fake core. The runner passes `MCIS_ACCEPTANCE_WEB_URL` to Node, which requires HTTP on 127.0.0.1 with an explicit port. Vite strictPort fails if another process claims the selected port. No external service or production data is used; the runner terminates its services and removes generated bundle/data.

Run from repository root:

```bash
PYTHONPATH=service \
MCIS_ACCEPTANCE_CORE=/absolute/path/to/actual/core-wrapper.sh \
MCIS_DOTNET=/absolute/path/to/dotnet \
/path/to/service/venv/bin/python web/tests/run-registered-network.py
```

Verified in the cloud environment:
- Four real requests preview/commit two fictional CSV originals (heading 45/50, shared timestamp).
- Two real registered preview requests (legacy unscoped and caller-declared scoped) traverses Vite/FastAPI/actual W2; frontend parser accepts the 5-degree conflict and `persisted:false`, `observationApproval:not_assessed`.
- One real request using the existing AgentService header identity receives 403.
- All dispatched requests supply fetch `cache:no-store`. This observes request configuration, **not browser cache behavior or a server Cache-Control guarantee**.
- A pre-aborted request rejects with AbortError and dispatches no fetch. This does **not** verify cancellation of already-running core computation.

Final run exited 0 with seven real requests. An initial test attempted nonexistent role Viewer and received expected service BAD_ROLE/400; the final test uses the real AgentService role to exercise authorization denial. Header identity remains a development mechanism, not production authentication. No browser, rendering, clicking, cross-tab behavior, real evidence, LLM, or persistent source certification is validated here.

The scoped request explicitly declares a fictional report source; this tests transport/echo only and is not an actual public-report extraction or verification. Both response scopes are checked by the frontend parser; the old request remains unscoped.

## Parent-report transport acceptance (2026-11-13)
The current runner adds six actual requests to the prior seven (13 total):
preview/commit the pinned published YANGZE22 PDF, preview/commit a CSV transcribed
from its figure27 True48 observation, linked single-source preview, and a linked
preview with intentionally wrong parent SHA (409). Both files are registered in
an isolated fictional demo case for test-only transport; this is not a new real
case investigation. The report hash and visual-review fixture are asserted before
registration. The actual frontend request/parser traverses Vite and FastAPI,
with the real compiled W2 for accepted preview. No fetch responses are mocked.
Returned parent SHA and user_declared_not_verified are checked; single-source
no-conflict result is NOT corroboration or evidence approval. The frontend caller
uses the actual parentReport payload; DOM selection remains covered separately
by HappyDOM, not this network runner. This adds no product code or permissions.
Old seven-request count above is historical. No browser visual/E2E, real LLM,
clock calibration, semantic extraction validation, CI or production auth claim.

Independent native reviewer reran the full13-request runner successfully(exit0),
with no blocking defect found. Primary and independent runs use fresh temporary
SQLite/storage. Test SHA256: f72e05b7ca41af964c974755a725793341cc7d7b4b22d5b6bc64bc792e7d95b2.
The test environment's evidence_preview.py Git blob matches remote b2207bd:
11420280b1b6ce6b3701dc152de3317aaefd81c9. No production code changed.
