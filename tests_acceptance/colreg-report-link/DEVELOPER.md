# COLREG report target — developer verification
Base main94d5e38c926fda232bb987b60fa9145e4bcf01a7, independent of other UI branches.
reports/sources.py:299 emits case/check/run query; ColregPage previously ignored
check/run and requested active with first check selected. Synthetic actual-page
execution reproduced CK-1 instead of requested CK-2 before modification.

Scope: query-keyed session, initial run/check selection, encoded run path;
explicit versions cannot fall back to current analysis, mismatched version/case
or absent check produces an explanation and explicit exit to current case view.
Unversioned links retain current-table semantics. Existing manual version picker
also no longer silently falls back if its selected version cannot be read.
Current-only old-service fallback remains. No backend, permissions, rule execution
or historical immutability changes. The notice states that source content and
original evidence have not been verified; reading run ID does not authenticate a
report-generation snapshot. Existing review/version activation actions unchanged.

Commands from web (new test individually reviewed):
```
node tests/colreg-report-link.test.cjs
./node_modules/.bin/esbuild tests/case-context.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-colreg-case-context.cjs
node /tmp/mcis-colreg-case-context.cjs
npm run build
```
Developer results: 9 synthetic page evaluations /12 assertions; 30 existing
navigation assertions; TypeScript/Vite build passed,766 modules, >1500kB bundle
warning retained. First intermediate test output mislabeled scenario count as8;
corrected to9 with unchanged12 assertions, rerun after final path encoding.
Actual page executes against synthetic hooks/router/load results, never HTTP.
Tests cover targeted run/check, pending/unavailable/mismatched run, absent check,
legacy check-only and ordinary current, changed-query session keys. They do not
prove real React remount timing, backend isolation, response integrity, manual
version switching/activation/review, or old-history semantics end to end.
Approved dependencies reused, no installation. No real case materials, models,
core invocation, paused nodes or write-refusal probes. Browser/visual and
independent acceptance pending; no merge or deployment.
