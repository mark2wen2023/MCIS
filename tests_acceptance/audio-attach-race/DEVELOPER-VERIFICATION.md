# Audio attach pending-input guard
Base: 2b5e19f3c4707970948388b58948c2ba3f44f0d3.
All five new nodes statically reviewed: synthetic DOM and deferred successful HTTP responses only, no server/browser/model/files/database. Baseline 4 failures and 1 normal-flow pass: editing, changed case, changed run, away/back caused old response to replace current page.

After fix: `node --test tests_acceptance/audio-attach-race/page.test.cjs` 5 passed. `node --test tests_acceptance/audio-read-selection/page.test.cjs` 1 passed. Targeted audio-save-context 4 and audio-saved-draft-state 3 passed using their documented name patterns. These developer counts overlap earlier checks and are not full-suite or independent acceptance.

Captures edit and selection epochs before importing; changed input/context retains drafts and requires manual result checking. Original request may have created a record; no cancellation, rollback or automatic retry is claimed. No paused, security, write-refusal or browser tests run. Drafts still only in page memory. Permission and archive protections unchanged.
