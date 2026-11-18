# Report review pending input — developer synthetic verification
Base main: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.

ReviewDialog disabled buttons while busy but left textZh/textEn/reason editable. ReportPage.submitReview closes the dialog on successful response (lines 118–126), discarding later local edits not included in submitted body. Actual ReviewDialog with synthetic hooks/submit callback reproduced acceptance of late changes under busy=true before fix. Parent close behavior was inspected statically, NOT exercised in a full page/HTTP/browser integration.

Minimal fix: readOnly={busy} on all three textareas, handlers preserve state while busy, and explicit waiting notice. Failure returns to editable inputs with submitted draft intact. No change to payload, policy, API, server state or default route; no automatic retry.

Developer commands (web, reused installed dependencies):
`node tests/report-review-pending.test.cjs` — modify and dismiss flows, 14 assertions passed. Rereads current returned input props; actual component with synthetic React hooks, no DOM/browser claim.
`npm run build` — passed, existing >1500kB chunk warning.

No paused/refusal/security tests, real records, core/model or service calls. No independent, browser/visual/accessibility or whole-system acceptance. Does not prove behavior of pre-busy-render queued events, cross-route navigation or unknown backend commit. Retention remains in page memory only. This main-based candidate changes ReportView.tsx, which also has unmerged report changes (PR104); no integration with those is claimed. Other navigation fixes were read back on remote and not duplicated. Freeze is limited to this slice.
