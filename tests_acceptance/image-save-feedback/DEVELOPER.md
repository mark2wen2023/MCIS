# Image save feedback — developer synthetic check

Base c76afd3e6b852198e2dac1b8d0d7d089d53db6e7.
Each row now retains feedback scoped to the loaded case/run/line: last confirmed revision,
current dirty input, pending save or unknown result. Input replaces stale generic success text;
unknown remains visible after further edits. Communication/response-check failures after dispatch
are conservatively unconfirmed, not proof of non-commit. Existing response validation is unchanged.
No retry, request cancellation, server receipts, unknown lock or concurrency guarantee added.
A deliberate new save remains possible as before; this is feedback, not enforced reconciliation.

Reviewed safety: new script imports Node built-ins, reads only HTML, replaces json() with controlled
memory Promises, forbids real fetch, and uses a synthetic preview.clear. No image decoding, Python,
model, case/seed files, application, server or browser. Adjacent existing scripts use in-memory
fetch doubles, not network. No paused/refusal nodes selected.

New command:
```
node --test tests_acceptance/image-save-feedback/page.test.cjs
```
Pre-fix: 0 passed / 5 failed: stale success after edit, vague communication failure, and missing
explicit unknown/old-run attribution in pending edit/case/run scenarios. Post-fix: 5 passed,
0 failed/skipped. Actual bound oninput, second controlled save, current DOM/dirty/state checked.

Separately reviewed adjacent regression command:
```
node --test tests_acceptance/image-saved-draft-state/page.test.cjs tests_acceptance/image-save-response-contract/page.test.cjs tests_acceptance/image-save-context/page.test.cjs tests_acceptance/image-task-waiting/page.test.cjs
```
26 passed, 0 failed/skipped. Separate from the five new cases; not full-suite or historical totals.
Existing response checks still compare with current fields, so editing during a successful response
can conservatively remain unknown. This slice does not change that contract or infer backend commits.
No build for standalone HTML; no actual HTTP, permissions, original files or browser acceptance.
Backend startup/archive pause unchanged. No merge/deployment. Independent review pending.
