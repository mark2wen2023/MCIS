# METADATA-ONLY RESEARCH — NO PRODUCTION WIRING

Review branch research/server-metadata-idempotency-review. Direct parent is fe3fb05515898cbde380af9bf819afcb344a28eb, verified against origin/codex/evidence-refresh-recovery-review. Parent chain retains d1a4424→3952a03→3aba2bf; no separate file security or PR69 stack is included. Only research prototype, tests and review/docs are added; service/mcis_service, contracts, default app and web have zero diff to parent.

No production migration is installed. install_schema is explicitly invoked only by synthetic fixtures; no app imports the prototype. No production HTTP route/config/provider changes, no original bytes accepted and no new filesystem write/delete. No actual SSO/credentials supplied. Test verifier and grants are clearly synthetic; source SHA is an unverified declaration. Result states contentStored=false/prototypeOnly=true. Store epoch/case generation provisioning and real identity remain release blockers.

## Reproducible checks

Requires existing service virtualenv with repository dependencies (no environment or key files included):

```sh
bash tests_acceptance/server-idempotency/run-review.sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests tests_acceptance/server-idempotency-independent/test_boundaries.py
```

The first command covers all17 candidate tests and5 independent probes (22 total). Tests use real temporary SQLite, domain/custody/audit functions, independent engines and child interpreters. Failure hooks/process exits are explicit synthetic faults. The full command also exercises unchanged existing service tests; retain baseline failures rather than suppress them. No production benchmark, network provider or power-loss qualification is implied.

The original independent failure and fixture setup errors are preserved. Strict Actor field validation and WRITE_LOCK-before-BEGIN ordering were repaired and retested before freezing. Frozen implementation hashes in logs/server-idempotency-research-hashes-frozen.txt. Ordinary SQL triggers protect research receipts; they do not defeat a malicious DB owner or stale backup restore.

Prior report's local-only/no-push wording describes the first research turn. Subsequent explicit authorization permits publishing this independent review branch, not deployment/merge or enabling metadata registration. No PR creation requested. Full-run results and baseline comparison are recorded below after execution.

## Full-suite and clean-parent comparison (completed)

Candidate:1585 passed,180 failed,11 skipped,104 errors (524.45s).
Clean detached parentfe3fb05:1563 passed,180 failed,11 skipped,104 errors (522.01s).
Independent mechanical comparison: all284 FAILED/ERROR node IDs and statuses match;
candidate-only0, parent-only0. Candidate adds exactly22 passing checks (17 prototype+5
independent). Both suites are NOT green. This supersedes older narrow baseline counts;
policy-denied fixture setup and domain-core/environment failures remain unresolved.
See ../server-idempotency-independent/baseline/comparison.json and both full logs.
Log trailing whitespace may be normalized for review; assertions/results are preserved.

No sensitive-pattern/path findings in staged sources/artifacts after review. Real
credentials, runtime databases and generated core outputs are excluded. Research
publication does not imply production safety, original-byte storage or real identity.
