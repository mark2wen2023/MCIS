# GISIS feedback ownership and delayed ordinary errors
Base 8d634cf4fd1775c696998574e46ce286eded15bc. Actual ReportSession synthetic callback harness independently reproduced (1) rejected transport promise after edit appearing as current field error; (2) editing GISIS clearing the unrelated completed glossary download notice. Both baseline assertions failed before modification.

Separate GISIS notice/error state from general feedback. Edit invalidates GISIS validation/notice/error only. Ordinary GISIS errors compare captured request/input revision before display; changed-input results use unknown-result guidance instead. Current ordinary failures remain visible; editing them clears their old error. The existing structured validation-failed detail mapping is retained in GISIS handling. HTTP 403 is explicitly rethrown into existing perform/handleError, never converted to a stale-field notice. No permission semantics or backend changes.

Developer commands from web:
- node tests/gisis-feedback-scope.test.cjs: 3 synthetic flows passed (late ordinary error; current ordinary error then edit; unrelated glossary notice preservation).
- node tests/gisis-parent-validation.test.cjs: 4 existing synthetic deferred flows passed.
- node tests/gisis-stale-validation.test.cjs: 4 flows / 44 assertions passed.
- npm run build: passed, existing large chunk warning.

Synthetic Error rejection and successful fake glossary result only. No HTTP, download, browser, permission/refusal tests, paused nodes, real data, models or services. 403 routing and structured error mapping were checked statically, not exercised. Parent harness skips startup effects and replaces ReportView; not full React/UI integration or independent acceptance. Existing positive tests repeated, not additive full coverage. No server cancellation, retry, authorization or persistence guarantee. Concurrent non-GISIS feedback ordering and full audit refresh remain outside this slice. Prior freezes stay historical.
