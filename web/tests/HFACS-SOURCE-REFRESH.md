# HFACS source refresh confirmation lifecycle

Base `94d5e38c926fda232bb987b60fa9145e4bcf01a7`. The existing changed-source editor allowed: refresh succeeds → acknowledge/select → refresh again fails → old source selection and acknowledgement remain, so save becomes available again. The old `refreshSources` cleared these only on success. This was established from the actual handler, not a browser reproduction.

The real Editor now uses the small `sourceReviewReducer`. Refresh start clears source selection and revokes readiness/acknowledgement before requesting. Failure leaves that state; only a current successful response makes sources available, and it still requires a new human acknowledgement. Both save button and save handler check readiness plus acknowledgement. Existing request generation/identity guards, pending-request retry semantics, backend version checks and permissions are unchanged. Existing source-rendering guard hides old metadata while unavailable. The “explicitly no source” message requires refreshed and acknowledged state, so a failed refresh cannot imply deliberate empty selection. Draft text/last saved version remain intact; no factual confirmation, policy, archive or storage change.

Linux commands from `web/`, using existing dependencies only:

```sh
./node_modules/.bin/esbuild tests/hfacs-source-refresh.test.ts --bundle --platform=node --outfile=/tmp/hfacs-source-refresh.cjs
node /tmp/hfacs-source-refresh.cjs
bash tests/run-hfacs-drafts-w184.sh
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

All exit 0. New test exercises the actual reducer used by Editor: changed initial state, initial successful refresh/acknowledgement, second refresh invalidation, failure with a stale acknowledgement attempt, successful retry requiring new acknowledgement, uncheck, and unchanged/none legacy initial behavior. Existing W18.4 model/digest/transport suite passed; its transport is mocked, no service write. TypeScript initially failed because the sparse checkout omitted the unchanged `contracts/schemas/report.schema.json`; materializing that exact source prerequisite resolved it. Vite emitted only the existing large-chunk advisory.

Neither react-test-renderer nor jsdom is installed. No browser launched, mounted React effect test, HTTP/backend/core/model, real data or actual save occurred. Reducer tests do not prove live rendering, keyboard or asynchronous React scheduling. Existing guarded response delivery is retained but not newly claimed as exercised here. Generated build/test outputs are not committed.
