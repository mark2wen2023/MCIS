# Actual parent-function source lifecycle — development evidence

Base: `759d14d9948d72152bb14855b6f921be6f7b9af2`, branch `test/interview-source-lifecycle`. This increment changes only tests and records. No product fix was required by these scenarios.

The new test bundles the actual InterviewPage, private child components, useContentLoad, InterviewView and SourceDisclosure. It traverses their returned JSX, invoking the real roster/detail loaders and identity checks. Complete synthetic roster/detail responses include both outer recordId and record.recordId. Only contentRequest is replaced with controlled memory Promises; global fetch throws and a non-undefined request body throws. Manual intake, provenance, agent panel and toast are inert seams; their behavior is not covered. No write handlers, permission-denial paths, backend, Python application, seed/case/media data, models or browser are invoked.

Five scenarios: valid B precedes late A success; valid B precedes late A ordinary error; outer recordId mismatch; inner record.recordId mismatch; loaded A followed by B with null source fields. Assertions inspect actual rendered SourceDisclosure descendants and links, require identity errors to suppress the source, and confirm cleanup aborts the old request signal. The memory transport deliberately permits late settlement to exercise the actual hook's live/generation checks.

Synthetic hooks, keyed instance replacement and cleanup are explicit test machinery, **not real React reconciliation, concurrent rendering, browser, HTTP or authorization acceptance**. A complete runtime schema validator is not exercised. Null sourceSha256 is a deliberate missing-field tolerance fixture (the TypeScript interface declares an optional string); no server contract is inferred from it.

Developer commands (existing dependencies reused; no install):

```sh
cd web
node tests/interview-parent-source-lifecycle.cjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

2026-11-18: 5 scenarios passed; TypeScript and Vite passed (767 modules; existing >1500 kB chunk warning). Initial test failed because synthetic EV-A/EV-B did not satisfy the product's EV-digits link rule; corrected fixtures to EV-1/EV-2 and reran. One intervening command used an incorrect working-directory-relative path and did not run the test. No product behavior was changed. This increment awaits independent review; do not sum it with prior-version counts. No merge/deployment.
