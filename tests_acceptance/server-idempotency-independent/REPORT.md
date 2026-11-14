# Metadata-only server idempotency — independent review

Target `/workspace/mcis-server-registration-idempotency`, parent `fe3fb05`. Research-only prototype, no HTTP mounting or identity provider implementation. Read AGENTS/handoff and actual prototype/test code. No reviewer product or prototype changes, commit, push or deployment.

## Actual execution

From `service`:

```sh
PYTHONPATH=. .venv/bin/python -m pytest -q --import-mode=importlib \
 tests/test_server_idempotency_research.py \
 ../tests_acceptance/server-idempotency-independent/test_boundaries.py
```

**20 passed, 1 failed in 5.48 seconds** (`results.txt`): 17 supplied cases plus four independent probes. Initial reviewer test setup omitted the imported local fixture, producing four setup errors; corrected only the independent test import and preserved `initial-fixture-errors.txt`. Final result above is the actual executed coverage.

Independent passing probes use real separate SQLite connections, existing case/Evidence/custody/audit models and explicit synthetic trust adapters:

* A raw SQLite writer reserves first, removes grants, then commits while registration waits at BEGIN IMMEDIATE. Registration sees the revoke, returns 403 and leaves zero evidence/custody/audit/receipt rows.
* Three independent engines concurrently submit the same scope/key with different titles: exactly one committed result and two 409 conflicts, one evidence/custody/audit/receipt. No overwrite.
* After an existing receipt, current evidence_meta Deny blocks both replay and recovery with 403; original 1/1/1 registration remains.

Supplied tests rerun here cover exact replay, different binding conflicts, independent-connection same-key coalescing, distinct-key ID allocation, faults before and after commit, generation change, serialized revocation, missing trust and content/path/role rejection. They do not store bytes. Failure after commit acknowledgement reconciles as committed, rather than falsely not_committed.

## Reproduced interface validation gap

Independent `test_verifier_actor_issuer_must_be_string` supplies an Actor with a nonempty list as issuer and otherwise valid fields. The prototype's actor check tests truthiness but not string type, the synthetic authorizer echoes the issuer, canonical scope serializes the list, and registration **succeeds**. Expected fail-closed 401 is not raised.

This is a trusted injected provider contract error, **not proof that an HTTP user can inject a verifier or impersonate an authenticated person**. Nevertheless dataclass annotations do not enforce runtime types. Actor issuer and subject should be validated as nonempty strings before authorizer/scope use; generation should likewise have a stated primitive contract. The passing fixture provider does not establish real SSO/issuer/signature trust.

## Architectural boundaries

Authoritative Evidence/custody/audit/immutable receipt use the same SQLite session and BEGIN IMMEDIATE transaction. Current authorizer and policy are checked before receipt lookup, including replay/recovery, so idempotency is not a bypass of current grant revocation. Missing receipt returns unresolved with automaticRetry/Delete false; absence is not labeled universal noncommit. The receipt validates current Evidence projection and Register/Change conditions, with trusted DB assumptions. SQL triggers prevent ordinary UPDATE/DELETE, not a malicious DB owner, rollback to old backup or physical DB replacement.

Scope includes configured store epoch, issuer/subject, case, authorizer generation and request key; metadata binding additionally includes operation version and projection. This works only if epoch and case-generation provisioning are trustworthy and stable across processes/restores. They are injected/configured values, not independently maintained production lifecycle machinery. A changed epoch intentionally changes scope; do not claim protection against duplicate creation if callers/deployments can arbitrarily pick epochs. Fixture grants are not a production membership model.

The prototype begins its SQLite writer reservation **before** entering service.append_custody's internal WRITE_LOCK. Some product operations use WRITE_LOCK then SQLite BEGIN. This is a potential mixed-operation lock-order inversion on future integration: one thread can hold the DB reservation waiting for Python lock while another holds Python lock waiting for SQLite. Existing SQLite timeout may break the wait with failure; it does not establish correct throughput or liveness. This review identifies source-level ordering, not a newly run deadlock exploit. Research-only non-mounting is important; integrate only after a coherent lock-order test/design.

## Strict scope and disposition

This is **supplied-SHA metadata registration**, not file registration atomicity. SHA is a declaration; no content is accepted, stored, hashed or authenticated by this experiment. No filesystem/DB commit coupling, object resolver, package format migration, automatic deletion or frontend persistent lock is implemented. Current metadata-only validation correctly rejects contentBase64, relativePath and client role keys in tests.

Identity provider integration, authenticated sessions, server receipt protocol/HTTP error contract, crash/restart and backup lifecycle, production cross-process configuration, full concurrency/lock matrix, expiry during long operations and resource admission remain unimplemented or unverified. Supplied faults are controlled injections, not exhaustive OS/power-loss durability tests.

Disposition: narrow idempotency/revocation/transaction tests pass; **runtime Actor issuer type validation fails independently**. Research remains blocked from production use regardless of that small fix. No full-file registration atomicity claim is supported.

## Research revision retest

Independently inspected revised Actor validation: issuer/subject now require strings with explicit length bounds before authorizer/scope use. `run` now acquires the shared reentrant WRITE_LOCK before session and BEGIN IMMEDIATE, retaining it through session exit/commit; this aligns the identified order with existing protected writer conventions.

Reran supplied 17-case selection (including actual subprocess same-key and os._exit before/after commit probes) plus original four independent probes: **21 passed in 6.03 seconds** (`retest.txt`). Original `results.txt` remains 20 passed/1 failed; malformed issuer no longer registers.

Added independent SQLAlchemy-event observation on fresh registration and receipt recovery: current-thread ownership of WRITE_LOCK is true at both BEGIN IMMEDIATE and commit for each operation. Expanded result **22 passed in 5.90 seconds** (`retest-lock-order.txt`). This is direct local lock-order observation on the current Python runtime, not exhaustive deadlock certification of all existing writers. The two runs overlap and are not cumulative unique coverage.

The reproduced Actor gap and identified prototype lock-order inversion are closed for this revision. Production remains unmounted, with synthetic identity fixtures and SQLite-specific research constraints. No file bytes are accepted or stored, and these results cannot be described as file registration/cleanup/FS–DB crash-atomicity fixes. Reviewer changed only independent test/report; no prototype or product changes, remote operations or deployment.

## Complete regression comparison (supersedes any smaller-suite baseline shorthand)

Independent clean-parent full run at fe3fb05: **180 failed, 1563 passed, 11 skipped, 104 errors, 522.01 s**. Coordinator candidate full run: **180 failed, 1585 passed, 11 skipped, 104 errors, 524.45 s**. Mechanical FAILED/ERROR node and outcome-type comparison found all 284 nodes identical, zero additions/removals/type changes; 22 added candidate tests pass. Full suite remains **not green**. See `baseline/REPORT.md`, complete logs and `baseline/comparison.json` for reproducible evidence and environment/fixture distinctions. The historical five-failure shorthand is not valid for this expanded scope.
