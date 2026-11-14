# Server registration idempotency: local restricted candidate

Parent/unchanged HEAD fe3fb05515898cbde380af9bf819afcb344a28eb. Local branch local/server-registration-idempotency. Only research module/tests/docs; no existing production module/config/schema/route modified. No push/merge/deployment.

## Outcome

A limited database-only pattern is feasible for **supplied-SHA metadata registration**: current trusted identity/grant and policy, serialized ID assignment, Evidence+custody+Audit+immutable request receipt in one SQLite transaction. Exact same scoped key/body returns one original result; changed body conflicts. Request scope includes server store epoch, issuer/subject, case generation and request UUID. Replays and recovery recheck current grant/policy; case generation changes reject old requests.

Default missing verifier/authorizer/config refuses503. Synthetic fixtures implement the test identity/grant, not SSO. No files/bytes/path accepted; result explicitly contentStored=false. Therefore this candidate is NOT evidence-original registration or a production auth/atomicity repair. Full file path remains blocked by separate filesystem+SQLite effects and missing trusted identity/lifecycle machinery.

## Actual tests

Selftest17 passed5.69s, real temporary SQLite/domain functions:
- Same key concurrent independent engines/connections returns one Evidence/custody/audit/receipt; different keys produce distinct evidence IDs.
- Two real subprocesses with barrier share one SQLite file/key and receive the same committed result; one registration. These processes do not share Python WRITE_LOCK.
- Failures injected after authorization/Evidence/custody-audit/before commit roll back all authoritative records; after successful commit but failed acknowledgement preserves receipt and reconciles without another registration.
- Real subprocess os._exit72 before commit yields unresolved/zero records; after commit yields committed/one set. Process exit is not power-loss durability.
- Another connection's revoke waits behind the transaction; after it commits, replay/recovery403. Earlier revoke denies before writing. Case generation change409; invalid identity/no provider refuses; bytes/path/client role fields rejected.

Independent first pass20 passed1 failed: verifier returning Actor with list issuer was wrongly accepted. Added strict string/length checks for issuer/subject. Source review also identified inverted DB/Python lock ordering. Candidate now takes WRITE_LOCK before BEGIN IMMEDIATE, consistent with existing append_custody writers; no premature lock release. Independent retest21 passed6.03s; added lock-order probe22 passed5.90s. Counts overlap selftests. Original failure/initial fixture-error logs retained, no discarded assertion. See ../server-idempotency-independent/REPORT.md.

No new HTTP endpoint was created: executable candidate tests call the service prototype with actual DB/domain services. No actual identity provider, proxy, model or production environment used. Entire pre-existing test suite/.NET not rerun; prior baseline failures and.NET absence remain.

## Semantics and blockers

Any unclassified commit/connection exception stays unknown; no automatic retry/deletion. Missing receipt returns unresolved, not proof of universal rollback. Precommit all-or-none assertions are test observations, not a generic HTTP failure classification. Existing current Evidence projection/registration mismatch yields409 even if historical receipt committed. Original records retained.

Trusted server adapters must honor transaction ownership. Local SQLite ordering does not provide distributed IdP revocation or cancellation of already authorized in-flight operations. Server store epoch and case generation are required interfaces, not production provisioning. Changing epoch changes scope; stale backups/imported receipts must not become live credentials. No general audit tamper proof, authenticated source provenance, capacity/timeout or power-loss guarantee. Full writer lock and memory/performance limits persist.

Do not wire this research schema into generic export/import: they do not preserve its receipt lifecycle. Full file ingestion still needs safe immutable-object publication/recovery and archive roundtrip, then trusted identity integration before release. No uncertain file is removed and no current workbench behavior changes.

Reproduce from service:
`.venv/bin/python -m pytest -q tests/test_server_idempotency_research.py`
Independent tests use PYTHONPATH=service from repo root. DESIGN.md specifies scope and preconditions. Disposition: restricted database transaction pattern validated; production/file registration integration BLOCKED.

## Authorized publication: complete service-suite rerun

The previous paragraph about not running the entire suite describes the original research turn. Before authorized publication, full service/tests plus5 independent probes completed: **1585 passed,180 failed,11 skipped,104 errors in524.45s**. full-review-tests.txt preserves the actual run. None of the17 candidate or5 independent probes appears among FAILED/ERROR nodes. These full-suite counts supersede the earlier limited "five baseline failures" statement; existing failures are much broader, including policy-denied fixture setup and unavailable domain-core behavior. No attempt was made to weaken policy or assertions to make them pass. Clean-parent comparison is recorded in REVIEW.md and ../server-idempotency-independent/baseline/.

Clean parent full-suite comparison completed independently:1563 passed,180 failed,11 skipped,104 errors522.01s. All284 failure/error nodes and statuses equal candidate; candidate-only0,parent-only0. The22 additional passes are17 candidate+5 independent checks. Complete service regression is NOT green; no claim that inherited failures are fixed. Authorized publication remains metadata-only research with no production wiring.
