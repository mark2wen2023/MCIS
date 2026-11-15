# Request-level budget development result

Base0ae2338, feat/request-level-durable-budget. Added request_budget.py with
separate schema; old Ledger/FourChair/LocalWorker/Pi/production unchanged.
Implemented: real SQLite atomic per-model-request reservation, ticket/context
binding, receipt digest binding, duplicates, unknown/pending and partial budget
exhaustion. All provider results are synthetic declarations. No actual dispatch
adapter added: dispatchAuthorized=false, providerExecutionVerified=false.

Exact command:
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
Final172 passed in1.88s including13 new request-budget cases. New tests use only
synthetic IDs/digests and temporary SQLite; prior local-worker regressions run
fixed Python children, not Pi/models/network. Initial11 request cases passed
before adding SQL failure and actual-commit/lost-ack fault injection.
Tests cover separate requests per turn, partial exhaustion, reopen pending,
wrong meeting/ticket/context, immutable receipts, no-refund stops, two-connection
single-new-reservation, total16, ticket rebinding/sequence, SQL rollback, and
synthetic lost acknowledgement after real commit. No restricted security tests.

No real provider receipt, credential, live request, independent review, browser,
production or billing verification. HOLD remains. A future actual adapter must
use per-request reservation before send, not merely reserve at process startup.
This candidate alone cannot guarantee correct external send/commit atomicity,
authenticate the caller, or authorize retry after missing/unknown records.
