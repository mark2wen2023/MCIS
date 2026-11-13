# IQ-1A backend-only candidate verification

Base main `3aba2bf03e393909c611489ae573a887087637ac`; PR44 is the design reference, not an implementation merge. No UI/LLM/browser, trusted identity, deployment or merge claimed.

Developer API suite: 28 passed. Independent reviewer ran those 28 plus 3 additional permission/archive/packet invalidation tests: 31 passed. It independently reproduced a stale-source bug in MoreVerification (old verification references were cleared before checking source versions). Fixed by checking original issue state before all RecordDiscussion outcomes; all three outcomes now have regression tests proving 409 and no state/events/receipts changes. Independent re-probe confirmed rejection and unchanged durable counts.

Broader developer regression: recommendation content access, interview access W52A, archive export safety and issue API: 150 passed / 22.85s. Earlier run had 117 pass/5 fail: new schema lacked `$id`, breaking global schema registry. Adding the canonical ID removed all five failures; a registry regression test was subsequently added. This record does not conceal failing pre-fix tests or claim CI/full repository coverage.

Local installed Python dependencies only, FastAPI TestClient with real SQLite. Covers restart persistence, round-bound hypothesis verification, non-unanimous discussion, reopening, current and historic sources, default role denials, policy revocation, actor-scoped idempotency, revision races, exact same-request races, atomic rollback, append-only SQL triggers, bounded JSON and pagination. Does not exhaust distributed workers, crash recovery, actual source bytes or adversarial database modification.

**Do not merge as a complete workflow:** saving issue state currently blocks `.mcase` export (including legacy exports) instead of silently dropping it; creation requires explicit acknowledgment. There is no issue package import/export or delete-to-unlock. Authorization is conservative all-category access using untrusted local role headers. Issue events are separate from global audit UI. No report integration or timeline calibration. Needs archive integration and user-facing UI before ordinary use.

Final candidate adds a registry loading regression: 29 issue tests plus 3 independent additions = 32 passed / 5.75s. Reproduce from repository root with `PYTHONPATH=service python -m pytest -q service/tests/test_investigation_issues.py tests_acceptance/IQ1A/test_independent.py` using existing project dependencies.
