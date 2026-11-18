# Reply/progress completion preserves newer input
Base f741dac278a6df047858ef8d17a1ad5e46893d66. Actual Detail's reply and progress callbacks each unconditionally cleared input on success. New synthetic test independently failed for reply and for progress after entering new text while the promise was pending.

Minimal change: local edit counters for response fields (party and text) and progress note. Successful completion clears only if that field group was not edited since submission. Different new text, edit-away-and-back, and party-only edits preserve input. Failed requests retain input as before. Submitted payload, permissions, callbacks and endpoints unchanged. No retries or cancellation added.

Developer commands (web):
- node tests/recommendation-form-save.test.cjs: 9 scenarios passed (reply/progress success, failure, newer text and ABA; reply party-only).
- node tests/recommendation-transition-note.test.cjs: previous four scenarios passed.
- npm run build: passed, existing chunk warning.

Uses actual Detail and actual useToast.run with synthetic hooks/deferred API results, inspecting freshly rendered input nodes and submitted payload. No HTTP, browser, real data, models or paused/refusal tests. Existing dependencies reused. No production/independent/visual acceptance. Does not validate backend concurrent writes, other forms, off-page draft persistence or the old transition action's identical-text ABA limitation. The parent already keys Detail by recommendation and case page by case/identity; cross-case lifecycle was not dynamically certified here. Same-file PR67/missing-reference candidates remain separate and require integration review.
