# Nonempty research listing / orphan association

Parent056dab67e1a7251892b80d58ff681983488f0de4. Independent research/restore-list-ledger-consistency, not PR104. No product source, permission or restore-enablement change.

Reproduced two ordinary synthetic failures on parent: captured normal old case plus unrelated orphan commit/readiness; individual old-case load succeeded correctly, but complete listing did not raise ReadinessUnknown. Two DID NOT RAISE failures in0.38s. Complete marked-store listing should not imply known association status when a separate ledger ID classifies unknown.

Correction: remove case-count condition on existing protocol/ledger-ID validation. Marked or expected-identity listing validates ledger associations whether cases is empty or nonempty. Error wording no longer says empty. No new ledger, repair, deletion, retry or ready promotion. Individual load remains case-scoped; consistent held claim can coexist with visible ordinary case. Unmarked legacy behavior unchanged.

Final command from service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_restore_classified_entries.py tests/test_restore_migration_protocol.py tests/test_conflict_readiness_gate.py tests/test_conflict_commit_observer.py tests/test_conflict_publication_observer.py
```
53 passed in32.07s. Three additional cases (orphan commit, orphan readiness, legitimate pending claim with old case),50 existing cases retained. All developer synthetic, not independent acceptance. No restricted security/ECFC operations, private originals, real model, actual crash/ambiguous commit, browser or production identity verification. Counts overlap prior runs.

This only closes the identified research-list association gap, not whole-database integrity, orphan business-row detection, concurrent snapshot proof, full endpoint coverage or production recovery. External identity retention, normal new-case registration and durable file publication remain blockers. Product409/422 protection unchanged. Old freeze entries for changed wrapper/test/contract are superseded by RESTORELISTLEDGER, not silently considered matching. No push, merge, deployment or PR104/body update.
