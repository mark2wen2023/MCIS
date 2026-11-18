# Interview + environment UI integration — DO NOT MERGE

Branch: `integration/interview-environment-ui`.
Exact tested code/merge commit: `290836391c3097bcac6e97e9709e17e3db58fc03`.
Parents, in order:
- `b1c4564d41c8ec4722eeefdda735465fafadcc0f` (#99 source disclosure + lifecycle tests)
- `813f9464849e621cfc6dcf2ba6a8f5717ce43c8e` (#101 origin guidance + explicit origin + input callback protection)
Common base/main checked: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.

This record is a documentation-only follow-up to the tested merge. Both complete histories are retained. Original candidate branches and main are unchanged. No PR104 or media-demo candidate is included.

Only REQUESTS.md and ROADMAP.md conflicted, as predicted. Resolution was exactly base bytes + #99 appended suffix + #101 appended suffix. Every other changed file was compared byte-for-byte against its supplying parent; all matched. No product conflict or new product edit. The later integration ROADMAP row records this result without altering either preserved suffix. Historical freeze files and acceptance records retain their original-version meaning; they are not blanket claims for this merge. Use the new freeze list for this candidate.

## Limited development verification (2026-11-18)

New isolated worktree, existing node_modules copied from the #101 worktree; no installation/network dependency retrieval. Before execution, the selected tests and their seams were reviewed: memory Promise/JSX/hooks for lifecycle tests, real static rendering for the two SSRs. fetch throws in all seven executions. The environment SSR imports frontend declarations but renders only ObservationList; it does not mount EnvironmentSession or invoke requests. Synthetic invalid metadata display checks are not HTTP permission/refusal tests. No backend, Python application, seed/case/media reads, models, browser, full suite, write-rejection probes or paused tests executed. Checking out the repository is NOT data sanitization; do not open/use real material.

Commands from `web` (individual processes, fail fast):

```sh
set -e
node tests/interview-source-lifecycle.cjs
node tests/interview-parent-source-lifecycle.cjs
node tests/environment-explicit-origin.cjs
node tests/environment-pending-input.cjs
node tests/environment-input-generation.cjs
node_modules/.bin/esbuild tests/interview-source-disclosure.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --outfile=tests/.tmp-integration-interview-source.mjs
node --input-type=module -e "globalThis.fetch=()=>{throw Error('fetch forbidden')}; await import('./tests/.tmp-integration-interview-source.mjs')"
node_modules/.bin/esbuild tests/environment-origin-guidance.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --loader:.css=empty --outfile=tests/.tmp-integration-environment-origin.mjs
node --input-type=module -e "globalThis.fetch=()=>{throw Error('fetch forbidden')}; await import('./tests/.tmp-integration-environment-origin.mjs')"
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

Results: lifecycle scripts individually reported 4 / 5 / 3 / 4 / 6 scenarios passed; both source SSR scripts passed; TypeScript passed; Vite passed (768 modules, JS 1859.00 kB, existing >1500 kB chunk warning). No failures or skips in these selected commands. Counts are overlapping scopes, not an aggregate or full-suite result. This is development verification, not independent acceptance.

The interview parent functions and validation execute, but keys/cleanup/hooks are simulated, not real React reconciliation. Environment events use captured callbacks and memory responses, not real event replay or server concurrency. The existing unknown readback semantics were not upgraded to operation receipts. No real browser, visual/accessibility, HTTP, production identity, clean install, full CI or archive/recovery acceptance. Backend startup/archive testing remains paused due seed-module import risk; this integration does not resolve it. No service/model activation, merge to main, or deployment is authorized by this document.
