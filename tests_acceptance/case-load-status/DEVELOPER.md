# Case metadata status feedback — developer verification

Base: main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.
The previous Layout assigns `online=false` on any case request failure and renders
`OFFLINE`; a missing/unavailable case is therefore presented as a service outage.
Success likewise only establishes metadata availability, not a health check.
This source-level finding requires no permission-denial request or real case.

Change: explicit lobby/loading/available/unavailable case-data labels, a visible
status region and explanatory title. Pending/error no longer receive the red
service-offline class. A successful value belonging to a previous case is rendered
as loading until the current case matches. Requests, authorization, identity and
navigation are unchanged. No simulation/ECFC capability added.

Developer commands, run from web on 2026-11-18:
```
./node_modules/.bin/esbuild tests/case-load-status.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/mcis-case-load-status.cjs
node /tmp/mcis-case-load-status.cjs
./node_modules/.bin/esbuild tests/case-context.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-case-context.cjs
node /tmp/mcis-case-context.cjs
npm run build
```
Results: 5 synthetic SSR scenarios / 27 assertions passed; existing case-context
30 assertions passed; TypeScript+Vite build passed (767 modules), existing-style
large chunk warning (>1500 kB) retained. Existing approved node_modules reused via
local symlink; no install/network dependency resolution. Initial esbuild version
command was mistakenly run at repository root and returned command-not-found;
the commands above ran from web successfully.

Not browser/visual/accessibility acceptance, independent review, live HTTP or
production authorization validation. No paused tests, refusal probes, models or
real case data. No claim that every navigation race or service error is solved.
