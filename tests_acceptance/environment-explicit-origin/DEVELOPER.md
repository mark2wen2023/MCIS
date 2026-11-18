# Explicit environmental source selection

Base PR101 remote feat/environment-origin-guidance: 1731de7217801d3e99af718a9cc0cc41c540f28a, checked unchanged before work. Independent candidate only.

New forms and Continue New begin with empty origin. Code-level builder guard prevents empty submission despite noValidate; persistent Observation stays the three-value enum. Existing records, zero vs omitted numeric values, text, server contracts and unknown-result verification unchanged. Older clients can still default Direct; this is not proof of explicit choice for historical records.

Development commands (web cwd):
```
node tests/environment-explicit-origin.cjs
node_modules/.bin/esbuild tests/environment-origin-guidance.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --loader:.css=empty --outfile=tests/.tmp-explicit-guidance.mjs --log-level=warning
node tests/.tmp-explicit-guidance.mjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```
New harness statically reviewed: real panel/builder with synthetic hooks/JSX, memory API and identity; fetch throws, no HTTP, cases, app/Python/model. First harness run exposed JSX-runtime test-double mismatch; corrected before product change. Then baseline failed Direct vs empty assertion. Post-fix three origin lifecycles passed: empty submit does not dispatch, input remains, explicit choices send same enum, zero/null/omitted/text preserved, records parse unchanged and Continue New resets. Existing origin-guidance SSR passed. tsc and Vite passed (767 modules, existing >1500kB chunk warning). Dependencies copied from existing /tmp/mcis-pr101-current/web/node_modules, no installation/download.

Existing W92 model and browser fixtures now explicitly choose Direct; their assertions remain and these scripts were NOT run this round. Only the listed reviewed tests ran, no paused/refusal/write probes. Synthetic hooks do not establish real React scheduling or browser interaction. No browser, HTTP, fresh install, backend/archiving, production identity, CI or independent acceptance. No merge/deploy.
