# Actual product increment: refuse uncheckable observation replacement

Base39b3113, fix/conflict-observation-source-guard. Changed timeline add_conflict
and revision bindings only. No new endpoint/receipt table/source disclosure; existing
policy unchanged. Same-ID a/b mutation refuses409 before writes. Old unjournaled
note/status edit preserves unknown source history instead of binding today's digest.
Existing A→B reproduction now expects refusal, history retains originalA only.
New-record declaration behavior is deliberately unchanged and is not verified reading.

Tests updated to new explicit compatibility contract without dropping assertions:
long history test now replaces summary with same observations; prior observation
replacement test asserts409/old value/one revision; A→B test refuses and keepsA;
source-version note test retainsA and rejects observation change after registryB.

From service:
PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_observation_guard.py tests/test_conflict_source_intent_gap.py tests/test_conflict_revisions.py::test_full_overwrite_and_long_revision_chain tests/test_conflict_revisions.py::test_source_version_kept_when_only_resolution_changes tests/test_conflict_revisions.py::test_legacy_baseline_is_unknown_not_invented tests/test_conflict_archive_readiness.py::test_existing_id_post_now_preserves_prior_observation tests/test_source_receipt_integration_gates.py::test_resolution_only_registered_source_revision_audit_rollback_together
10 passed in1.71s. Ordinary synthetic HTTP/SQLite, includes a/b-side refusal and zero
mutation, unchanged-side POST, Investigator note/status retained permission, legacy
first and subsequent note unknown bindings, A→B and existing rollback. No restricted
security/ECFC suite, source original files, browser, model or independent acceptance.
No claim of full suite success. No actual source observation editor was introduced;
external clients must handle409 without discarding local inputs. Current web PATCH
flow untouched. No audit/receipt signing or original-byte verification. No merge/deploy.
