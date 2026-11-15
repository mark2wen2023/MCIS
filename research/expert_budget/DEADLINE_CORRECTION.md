# Absolute deadline correction on ff310ad

Independent review supplied start=4194262.256341955. At now=start+600,
subtraction returns599.9999999995343. Prior elapsed subtraction left the
pending turn active. Store deadline=start+600 once and compare now>=deadline.
This uses the clock's representable absolute timestamp, without an epsilon that
could expire early. Boundary tests use math.nextafter immediately before/after
that timestamp, as well as equality; before remains active, equality/after stop.
Late submission is rejected, pending declaration becomes unknown, no budget refund.

Developer command:
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
Result:139 passed in1.18s, including3 new synthetic boundary cases.
No real API, credentials, browser, Pi execution or restricted tests involved.
Only four-seat simulated chair changed; other protocols are not certified by
this fix. Cooperative checks still are not a hard timer/cancellation mechanism.
Opinions remain memory-only, real four-expert execution HOLD. Independent
verification of this correction remains pending. Original freeze retained as
historical; use EXPERTFOURCHAIR-deadline-hashes.txt for changed implementation.
