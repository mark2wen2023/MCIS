# Evidence list metric read states

Parent: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.
EvidencePage previously used `ev.data ?? []` for all four list metrics, so initial
loading and a rejected read displayed the same zeros as a successful empty list.
The actual page now uses EvidenceMetrics: pending and unavailable are nonnumeric;
successful empty/nonempty lists retain their original counts and units.
An error takes precedence and its raw text is not rendered by these metrics.

Only the four evidence-list metrics change. Custody, conflicts, request handling,
permissions and same-case refresh behavior remain unchanged. The existing hook
retains the last successful data while a same-case refresh is pending; this change
does not add a loading signal or certify that retained data as freshly read.

Using existing installed dependencies, from `web/`:

```sh
./node_modules/.bin/esbuild tests/evidence-metrics.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/evidence-metrics.cjs --log-level=warning
node /tmp/evidence-metrics.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

Ten synthetic SSR assertions exercise the production metric component. No API,
real identity, database, archive, report, mounted effects or browser is exercised.
Case/identity invalidation and late responses still require the separate mounted
EvidencePage acceptance gate; these SSR tests do not claim that gate passed.
