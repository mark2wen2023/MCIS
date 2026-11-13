# Registered preview candidate case scope

The source selector now filters local-intake candidates to the active case and
requires a lowercase 64-digit current SHA-256. It previously checked only the
local-intake path, so a mixed-case manifest could render foreign titles or two
identical evidence IDs. This is a defensive UI correction, not a new backend
permission boundary; the existing server still owns case lookup and access.
Review-required and mismatched sources remain visible but disabled. Same-case
records with missing/invalid SHA and legacy archive paths are not candidates.

Before the change, the new HappyDOM regression exposed foreign/unknown-case
items, invalid SHA entries and duplicate IDs; after the change all 8 new checks
pass, including navigation to a different or empty case. Existing primary 53,
parent-report 48 and source-reset 15 checks pass (overlapping, not additive).
Two old synthetic fixtures were corrected to include the mandatory EvidenceItem
caseId, not by loosening production filtering. TypeScript/Vite build passes;
targeted lint has the two existing set-state-in-effect warnings. No new browser,
backend, LLM, CI, full-system acceptance, merge or deployment claim.

Run test with the same esbuild/HappyDOM setup as registered-acceptance/run.sh,
substituting tests/candidate-case-scope.tsx as entry.

Independent reviewer reran 8/53/48/15 and build, and added 19 hash/mixed-case/
case-switch boundary checks in web/tests/candidate-scope-review.tsx; all passed.
All these are local HappyDOM checks, with no server/LLM responses used for the
new selector tests. Counts overlap. No production data access incident claimed.
