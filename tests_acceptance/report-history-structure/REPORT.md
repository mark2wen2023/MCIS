# Fail-closed v1 report history structure

Local isolated follow-up on efbf517d22c4302b378323401bb866e07d3371fd.
PR95 -> ac0dfe1 -> efbf517 dependency remains. No push/merge/deploy in this task.

Independent review reproduced deleting citation href and changing historical fields without
rehashing: audit-list and snapshot GET returned altered content. Tightened permissions still
returned 403. This is an integrity bypass, not proven permission bypass.

Implementation replaces optional-key shape inference with explicit action-selected schema
validation and typed traversal of report, section, sentence, citation and nested review
before/after. Missing/incorrect types, absent bindings, wrong context, misplaced history,
source removal and version downgrade fail 409. The owning report's current/review source
inventory and identities constrain audit snapshots. Generation audit context constrains
live report downgrade. Audit event snapshot_ref determines ownership independently of the
mutable snapshot's reportId/auditSeq; missing referenced rows fail audit-list closed. Real
legacy generation+report data remains readable without inventing snapshots. Permissions
run first and remain unchanged.

Reproducible tests: service/tests/test_report_history_audit_integrity.py, synthetic real
TestClient and temporary SQLite. New cases include the exact href-delete attack; kind/id/
history deletion; wrong payload/field/container types; deleted/empty containers; misplaced
bindings; removing version+all history; nested and partial review attacks; legitimate
section modification; erased owner/changed audit sequence/deleted row; live downgrade.
The pre-existing legacy fixture now removes v1 data from BOTH report and generation row,
representing actual legacy instead of a downgraded current report. Explicit downgrade
rejection assertions are separate. No assertion is weakened to permit the attack.

Earlier 50 pass / 59 fail baseline/candidate comparison remains exactly that: matching
failed test IDs only, causes not individually established. Not full-suite success.
No browser or frontend changes; real browser, SSO, model/HFACS, production performance,
external clients and recommendation archive roundtrip remain unverified/blocked. Added
schema/context walks and DB reads retain existing authorization locks and add overhead;
no latency/concurrency/memory-budget claim. Integrity requires available stored contexts;
coordinated rewriting of every mutable context is not prevented by unsigned hashes.

Verification sequence: expanded selected regression 164 passed in 136.11s. Following the
last parent-context read and outer snapshot-envelope validation refinements, 5 targeted
checks passed (30 deselected) in 11.40s; final complete history-focused run recorded below.
No elapsed test duration is presented as production performance measurement. Earlier
in-progress legacy test failed correctly when only its live report was downgraded; after
making that fixture genuinely legacy, selected regression passed. Independent re-review
is required; author tests are not independent acceptance.

Final frozen-source history run: 48 passed in 76.47s (frozen-focused.txt), including all
35 audit-integrity cases and 13 source-history cases. Expanded 164 run preceded the final
parent-context/envelope refinements; final 48 validates those refinements. Do not present
that expanded run as a fresh full regression of the final frozen tree.
