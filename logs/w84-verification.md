# W8.4 verification summary

Base main: `8235918c6b7ebc7abac25a2a31b37e9104b63f3b`, retaining W19.1/W9.2/W10.1.

- Full service suite: 753 passed.
- All frontend model/render/navigation suites: 1,180 assertions passed.
- TypeScript, lint and production build succeeded, with documented existing warnings; not a zero-warning claim.
- Independent backend: 43 passed, plus 4 existing contract tests.
- Independent real-backend browser: 39 passed, including three responsive sizes, late mutation responses, current-case shell refresh, conflict comparison/rebase and unknown-result operation/source/reason validation.
- Additional independent legacy blank/empty-title reproduction fixed and retested through the real UI, save and reload.
- Additional mock browser lifecycle checks: 33 passed, not a replacement for real-backend tests.
- Existing independent environment HTTP: 47 passed; knowledge HTTP: 52 passed.
- Backend v2 and UI v2 frozen hashes match the final implementation.

D01 clarified the existing package format's absent/empty-string normalization and non-portable revision tokens; source text, empty meaning and full audit records are verified. Package serialization was not changed. D02 fixed read validation blocking repair of legacy blank titles; new blank writes remain rejected. Original failed attempts are retained locally, not misreported as passes.

Only five workspace text fields are editable. Time/epoch, coordinates, classification, case identity and fictional flags stay read-only. Sources/reasons are human declarations, not verified facts. Original evidence/reports and previously generated report snapshots are not modified. Local demo roles are not production authentication. No deployment or real incident edits were performed.

Reproduction and independent review: `tests_acceptance/W84/README.md`, `DEFECTS/W8.4.md`. Raw logs and screenshots remain local; only this bounded summary and reproducible tests are published.
