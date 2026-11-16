# Isolated migration/reopening protocol — developer only

Parent2b4edd94f97a0c96c9fdcd11265fd8afd8be5436, not PR104. Independent branch research/restore-migration-protocol, isolated worktree /tmp/mcis-archive-readiness-review. Existing long parent dependency chain is unchanged; this is not a clean-main integration. Production modules and default app untouched, unsupported409/422 preserved.

Implemented: singleton version/database identity and pre-existing ordinary-case inventory, created in one explicit BEGIN IMMEDIATE transaction; refuses prior restore operations and repeated/partial activation. Reuses existing temporary PendingReadinessStore, operation/commit markers and directory observer. No parallel restore ledger. Read classification requires explicit legacy mode or expected external identity; expected-marked databases with missing tables, wrong version/identity, orphan/inconsistent bindings remain unknown/held. Existing captured ordinary cases go to existing policy, not automatic authorization. New unregistered normal cases remain unknown in this research; production normal-case registration is NOT wired.

All existing restores remain held. Commit without matching pending metadata is unknown. Claim without commit after an attempt remains unknown-outcome observation, never confirmed rollback. Matching file inventory and DB commit remains restore_ready=false. No publish/ready/delete/retry API. Receipt history remains separate and inactive, registry hashes do not verify originals.

External expected identity is currently an explicit argument, NOT protected persistent deployment configuration. The DB marker alone cannot detect deletion of all state plus loss/change of that external expectation. Activation assumes a deliberately selected legacy upgrade; it cannot prove legacy if historical operation evidence was already lost. Do not turn this assumption into automatic product migration. Writer exclusion, safe no-replace publication, directory durability and every product endpoint gate still require implementation and review.

Command, from service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_restore_migration_protocol.py tests/test_conflict_readiness_gate.py tests/test_conflict_commit_observer.py tests/test_conflict_publication_observer.py
```
Final40 passed in29.20s. Includes15 new parameterized cases and25 prior cases, not40+15. Initial10-case candidate passed6.87s before adding five cases and tightening metadata association; final40 result supersedes it. An initial wrong-directory command failed to find the test file (exit4/no tests); corrected before actual execution.

New coverage: explicit legacy/default-unknown modes, existing case retained after activation, unregistered new case unknown, wrong identity and version, repeat activation refusal, atomic activation rollback including DDL, missing individual/all protocol tables, prior restore not reclassified as legacy, restore rollback before commit with files present, DB commit with files absent, response lost after commit, matching files and later missing marker, inconsistent commit/pending association and fresh-process reopening. Fixtures use synthetic temporary files and SQLite only; no real original or private case data. Observation does not mutate file bytes/counts in the asserted ordinary scenarios.

NOT verified: actual process crash, genuinely ambiguous SQLite commit, concurrent directory mutation, production deployment migration, complete product access isolation, original-file authenticity, browser/Word, real identities/LLM/HFACS. Separate snapshots are observational and cannot authorize readiness. No restricted security/ECFC retry or PR-body update attempted. No push, merge or deployment. Candidate needs independent review.
