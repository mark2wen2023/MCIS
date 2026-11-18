# Environment input generation — development evidence

Base `368b3d1bd3b740a888af4eabac41adc80ef6bceb`; independent branch `fix/environment-input-generation`. Product change is limited to CreateObservationPanel input callbacks. No backend/schema/permission/old-record changes.

Controlled Promise tests reproduced retained pre-submit callbacks mutating hidden or new form state after completion (before/after rerender), after continue-new (before/after rerender), and after ordinary communication failure before rerender. The pre-fix assertion listed all five windows. An earlier command used an incorrect relative path and did not create/run the test; no application ran.

A separate formEpoch is captured at render but advanced only in begin/finish/reset events. Input callbacks require matching formEpoch in addition to existing busy/alive/identity/pending/saved checks. Request epoch/live(n) is unchanged. This does not introduce retries, cancellation, server versioning or change existing readback semantics.

Safety review: only the actual component/model are bundled; React hooks/JSX and API are memory doubles, fetch throws. No backend imports, media/case/seed reads, models, browser, permission/refusal responses or write-rejection probes. Synthetic api.post records a local object and settles a local Promise. The unknown scenario uses an ordinary Error, then the existing verify path with an empty memory list. This exercises current UI unlock semantics, NOT proof that a request never committed. No permission-refusal recovery was executed. Local validation failure remains editable; fresh callbacks after continue-new and existing empty readback remain editable; pending unknown inputs remain blocked. useEffect is a no-op in this harness: unmount/real React reconciliation, event replay, batching and concurrency are not validated.

Commands, existing dependencies reused (no new install):

```sh
cd web
node tests/environment-input-generation.cjs
node tests/environment-pending-input.cjs
node tests/environment-explicit-origin.cjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

Development results 2026-11-18: new 6 scenarios passed; adjacent pending-input 4 and explicit-origin 3 passed (separate scopes, not full-suite coverage). TypeScript and Vite passed, 767 modules, existing >1500 kB chunk warning. No real React/browser/HTTP/production identity acceptance. Independent review pending. No merge/deployment.

Pre-existing untracked `.tmp-explicit-guidance.mjs` was not modified, run or included.
