# Archive scope wording and ordinary UI tests

Independent branch fix/archive-scope-copy-tests; exact parent
cf80623bf8d8ae564ccc904637c5dc71a055680f -> b23c7b6 -> e68bacc -> 2cb43812 ->
94d5e38. Requires the bounded1.4 candidates; not a standalone patch for main.
Remote main checked94d5e38. No push/merge/deployment in this task.

## Diagnosis and authority

Reproduced both failures before editing this complete local checkout:
- package-hfacs-w186.test.tsx: PackagePanel assertion `不是全系统备份` fails.
  Actual static visible text is `不是完整案件备份`, which already expresses the
  non-complete-backup boundary. The test's literal is obsolete, not a missing warning.
  Replace that literal with the actual warning and ADD whole-package refusal/no
  silent omission assertion. HFACS summary/panel original scope assertions remain.
- archive-guard-ui.test.tsx: `笔录仅在1.2.0受限归档...` fails. Actual text already says
  `匹配版本` and permits1.3 with W10. The exclusively1.2 expectation is obsolete.

Git blob identities of these two tests and PackagePanel/InterviewPage are identical
across main94d5e38, e68bacc, b23c7b6 and cf80623. Thus these are inherited literals,
not regressions introduced by restored-event provenance or timeline-only selection.

Separately the current notices omit the candidate's bounded1.4 combination. Authority:
contracts/track-history-v1.md §2 defines1.3 with workingv2/track history;
contracts/report-timeline-archive-v1.md defines1.4 with timeline, workingv1 and
no track-history combination, including timeline-only aftercf80623.
Update the four existing notices (report, interview, package panel, export panel)
to specify1.2 without either history,1.3 with track history/no timeline,1.4 with
timeline/no track history, and refusal when both occur. Existing complete-validation,
default-policy, original-preservation, inactive-receipt and non-current-review
warnings remain. These versions are conditional scopes, never `version or above`.
No API, parser, permission, storage or restoration implementation changed.

## Developer tests (synthetic/local)

From web, bundle each TSX test using:
```
./node_modules/.bin/esbuild tests/<name>.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-<name>.cjs --jsx=automatic --log-level=warning
node /tmp/mcis-<name>.cjs
```
Results:
- package-hfacs-w186: model/render/scope suite passes (runner does not count asserts).
- archive-guard-ui:29 SSR/error-mapping assertions pass, including newly explicit
  version scopes, rejected mixed combination and retained warning assertions.
- bounded-timeline-intake:68 synthetic model/SSR assertions pass.
- `python tests/archive-version-copy.test.py`:16 source assertions pass across all
  four notices, retaining warning checks and rejecting open-ended version claims.
- `npm run test:w16`:148 existing synthetic report assertions pass.
- `npm run build`:TypeScript and Vite pass; existing >1500kB chunk warning remains.
A first esbuild invocation from repository root failed to find node_modules; corrected
to web before the actual tests above. No dependency installation or environment change.

## Not verified / handoff boundary

All tests are developer-side synthetic/static/source checks, not real browser, real
HFACS/model execution, or full backend acceptance. No backend tests rerun because no
backend change. Previous91 backend passes belong to parentcf80623, not a new run.
Browser fixture's obsolete locator updated, but browser script NOT executed; its
existing launch configuration was not used or changed. No sandbox bypass attempted.

Build used this complete local Git worktree and its existing dependency link. This
is not the earlier independent e68bacc build with mixed source files and does NOT
resolve the cross-environment frozen-source handoff/independent-build limitation.
No new Library upload or alternative delivery attempted. Independent acceptance and
real browser page identity, layout, interaction, console/screenshot checks remain due.
No restricted historical-integrity or ECFC operation was repeated.
