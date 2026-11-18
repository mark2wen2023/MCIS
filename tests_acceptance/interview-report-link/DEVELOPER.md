# Report citation to interview selection — developer verification
Base main 94d5e38c926fda232bb987b60fa9145e4bcf01a7, independent of other UI candidates.
Source evidence: service/mcis_service/reports/sources.py around332 emits
_url('interview', case=case_id, id=rid, statement=sid). ReportView.tsx renders
citation.href. InterviewPage.tsx previously consumed only record, so id could
silently select the first roster item (or the fictional demo's IR-03).

Minimal change accepts id as an alias only when record is absent. Explicit record
(including its existing empty-string behavior) retains priority. Manual selection
still writes record; case scoping/loaders/permissions unchanged. A requested missing
record stays selected for existing detail handling, not replaced with another record.
No statement-row positioning, historical revision binding, original verification,
or evidence-support judgment implemented. This resolves record selection only.

From web, individually reviewed tests and synthetic imports:
- node tests/interview-report-link.test.cjs
  Before: actual InterviewPage selection IR-001 instead of requested IR-002 failed.
  After: 6 scenarios passed: report id, manual record, explicit precedence,
  missing reference, no reference normal case, existing demo default.
  Loads actual page functions with synthetic hooks/router/roster; detail components
  and HTTP are not executed. No real-case data or permission/refusal probes.
- ./node_modules/.bin/esbuild tests/case-context.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-interview-case-context.cjs
- node /tmp/mcis-interview-case-context.cjs : 30 assertions passed.
- npm run build : TypeScript/Vite passed,766 modules; >1500kB warning retained.
Approved existing node_modules reused; no installation. Developer results only;
not real browser, visual, live backend or independent acceptance. No models,
paused tests, write-refusal probes, merges or deployment.
