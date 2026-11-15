# Four-seat controller development record

Base 2a04125f03b12453e55b09b84f9362011fc49302, parent c1597bc (ledger),
then main94d5e38. Independent branch feat/four-expert-offline-chair.
New separate protocol: contracts/expert-four-chair-simulation-v1.md.
Existing two-role controller, packet and four-role ledger unchanged.

Run from repository root:
```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
```
All outputs supplied by tests are explicitly synthetic. No network/model/Pi,
credentials, production configuration or restricted security tests were used.
Tests cover all four seats/two rounds, prior round isolation, minority labels,
partial/failed/unknown/stop/deadline, immutable return copies, ticket binding,
SQL failures, no-resume, one concurrent reservation and malformed outputs.
No true provider call, cost/token accounting, durable opinions, crash recovery,
trusted authorization or hard cancellation has been implemented. The persistent
ledger records declarations; the completed phase means simulated opinions only.
All labels remain unverified even when unanimous. Independent review pending.

Final developer run: 136 passed in 1.04s (12 new four-chair cases included;
not independent acceptance). No failures/skips in this selected set. Not a full
service suite or production performance test.
