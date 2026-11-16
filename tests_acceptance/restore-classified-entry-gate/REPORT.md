# Research entry classification — developer only

Parent a92d346b1a1fdba87e211205d0a4ee3404a12b72. Branch research/restore-classified-entry-gate. This is on the existing long research chain, not PR104/main integration.

Reproduced ordinary synthetic discrepancy before change: activate synthetic-db, then insert SYNTHETIC-NEW; classify(expected_database_id=synthetic-db) returned unknown while old readiness_gate.load_case returned the new row. No production original or permission probing.

Changed only research wrappers: load_case/list_cases/scoped_call use classify whenever identity/mode is explicit or a migration metadata table exists. Omitted identity on marked DB is unknown. Pending load/callback raises CaseNotReady; unknown raises ReadinessUnknown and callback is not executed. List excludes known pending rows, but any unknown row causes an explicit whole-list error rather than misleading partial success. An individually captured ordinary case is still readable with the correct identity. Empty marked DB validates identity/schema rather than silently returning[] on malformed metadata.

Unmarked/no-identity callers retain original research behavior for compatibility. This does NOT detect total metadata loss if caller also loses/omits external identity; deployment must retain/pass that identity. Direct decision(), direct product case services and all actual endpoints are not globally intercepted. Product app imports none of this gate. No production permission or visibility behavior changed, no ready promotion, no experimental import enabled.

Five new ordinary tests cover old-case compatibility, post-migration unregistered new case unknown across three wrappers, callback nonexecution, held restored case, original unmarked compatibility, identity/mode mismatch, missing schema and malformed empty ledger. Synthetic callback verifies dispatch boundary only, not endpoint authorization. New ordinary-case registration is still absent; production cannot adopt this gate until that transaction and every endpoint/caller are wired. Keeping the same Session does not prove an explicit SQLite read snapshot. Existing caller transaction/policy obligations remain.

Final command from service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_restore_classified_entries.py tests/test_restore_migration_protocol.py tests/test_conflict_readiness_gate.py tests/test_conflict_commit_observer.py tests/test_conflict_publication_observer.py
```
45 passed in27.02s (five new plus40 existing), developer synthetic tests, not independent acceptance. Earlier27 passed before final empty-schema case/check; final45 supersedes it. Initial wrong-cwd invocation failed discovery with exit4/no tests and was corrected. No actual crash/ambiguous commit, browser, production identities, original-byte verification, HFACS or model run. No restricted security/ECFC retry, no PR-body update/retry, no merge/deploy/push.

Old CONFLICTREADINESSGATE freeze's readiness_gate.py entry and RESTOREMIGRATIONRESEARCH contract entry are intentionally superseded; do not claim those original manifests all match. New freeze RESTORECLASSIFIEDENTRIES covers current wrapper/contract/new tests. Earlier research modules/tests unchanged.
