# Request handshake development verification

Base2b0fa0b. Independent feat/worker-request-budget-handshake. Adds pinned worker,
its bounded two-way supervisor and tests; imports existing RequestBudget and exact
historical ownership module already in local_worker. Previous code untouched.

Command:
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
180 passed in2.72s, includes8 new cases. Intermediate6 cases passed in0.85s before
lost-ack and cancellation cases. Developer tests, not independent acceptance.

Actual OS child processes with fixed synthetic request/result messages were run.
Tests inspect committed SQLite pending row at every actual GRANT write, assert
four child processes cause8 request reservations, and observe PID/leader exit/reap.
They cover prior-role preservation and unfinished seats for third-request budget
exhaustion, duplicate request, pending-response timeout; SQL insertion failure before
grant; synthetic loss of acknowledgement after real reservation commit; cancellation
after actual grant. No network, credentials, real model, Pi or restricted tests.

A fixed first-round local role completion is NOT an expert opinion. No PDF/public
case was sent; existing pinned packet SHA is a binding label only. Provider receipt
is synthetic. No browser/production test, cross-process recovery, hostile reaper or
whole-descendant termination verification. Real integration still requires trusted
managed credential bootstrap and Pi canonical tool/request adapter, source/context
and opinion validation, bound dispatch ownership and durable role-result recovery.
Do not change quota2 silently to accommodate historical3–4 request live workflows.
