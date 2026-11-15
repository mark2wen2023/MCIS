# Actual backend registry receipt/observation submission candidate

Baseaa107b5, feat/conflict-registry-receipt-submit. New persisted receipt table and
strictly authorized issue endpoint, optional sourceReceiptId consumed in existing
same-ID observation POST transaction. Existing no-receipt409, current-version428/412,
and ordinary PATCH permissions remain. This is registry metadata, no file reading,
no proof of human reading, verified identity or truth of an observation.

Actual HTTP/SQLite tests, temporary synthetic cases:
PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_source_receipt_submit.py tests/test_conflict_observation_guard.py tests/test_conflict_source_intent_gap.py tests/test_conflict_revisions.py::test_full_overwrite_and_long_revision_chain tests/test_conflict_revisions.py::test_source_version_kept_when_only_resolution_changes tests/test_conflict_revisions.py::test_legacy_baseline_is_unknown_not_invented tests/test_source_receipt_integration_gates.py::test_resolution_only_registered_source_revision_audit_rollback_together
Run from service.18 passed in3.06s, includes9 new cases, not independent acceptance.
Earlier12 before adding legacy/concurrent cases. No full suite claim.

Coverage: issuance, app restart preserving receipt, same-transaction consumed revision
and audit association; unchanged-side history; two sources with one change;A→B/ABA;
exact expiration; different proposed input; existing Investigator source denial with
ordinary note success; unknown/no receipt rejection; injected failure AFTER actual
receipt consumption flush with external marker assertion, all data/audit/revision
rollback, explicit re-submission after proven rollback; legacy unknown preimage and
new postimage; concurrent same-token201/412 with one revision/consumption.
No restricted history/security/ECFC suites or original files used. Failed inputs
remain HTTP caller's responsibility; tests don't prove external UI draft retention.

Opt-in source issue route retains stricter existing policy, does not replace editable
permission. No new source editor or receipt UI; existing handling note/status flow
untouched. No automatic retries. Receipt retention/volume, real identity, original
bytes, production concurrency/performance, browser and independent review unverified.
Existing conflict archive refusal stays; isolated archive parser candidates require
future review for hash-covered sourceReceiptId and receipt data, not modified here.
No merge/deploy. SHA/source metadata supplied by caller cannot stand in for receipt.
