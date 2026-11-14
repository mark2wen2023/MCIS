# IQ read-only review snapshot: independent review

2026-11-14. Synthetic FastAPI TestClient and temporary SQLite only; no model, network, browser, production identity, deployment or case-fact acceptance.

Reviewed current hypothesis / verification-event joining, current and historical source access, preservation of text and source ordering, read-only policy and response caching. Found a design risk in an initial explicit ordinary `BEGIN`: it caused the existing authorization helper to skip its reserved-writer `BEGIN IMMEDIATE`. The implementer removed it before this test execution. No claim of an executed pre-fix failure is made.

Added five independent tests in `service/tests/test_issue_review_independent.py`:
- Existing permission revocation remains serialized: pause response projection after authorization, attempt policy revoke on another thread/connection, prove it cannot commit before response projection is released; next request is denied.
- Full-content read-only role can read without mutation authority.
- Removed historical-only source denies even after current hypothesis no longer references it.
- Reversed source input order does not falsely break the event join; original event ordering retained.
- Result text with approximate qualifiers/newline is preserved exactly (synthetic preservation text, not real-case model evaluation).

All 5 independent tests pass. Combined original 29 + new developer 11 + independent 5 = 45 passed / 13.22 seconds. Command from workspace: `PYTHONPATH=hypothesis-line/service mcis-work/service/.venv/bin/python -m pytest -q hypothesis-line/service/tests/test_investigation_issues.py hypothesis-line/service/tests/test_investigation_issue_review.py hypothesis-line/service/tests/test_issue_review_independent.py`.

Reviewed file SHA256:
- router.py `56ee956878080db064c481a00777d8020cd20f14bdd4819e9539cd21ab80d60c`
- review.py `767e1f5aab81a2ee3d45a0be010d7e133bed86ddd5d9a6c5b0b20433a8380a33`

No remaining blocking finding for this limited read API. Does not add a user-facing UI, model reasoning, source-byte verification, full archive integration or production authentication. The old case export restriction stays necessary. Direct database corruption is not a supported workflow and this projection is not an audit-chain certifier. Concurrency test covers local SQLite connections, not distributed servers or all revocation schedules.

Final rerun after developer added verification-overwrite/history regression: original 29 + developer 12 + independent 5 = **46 passed / 10.90 seconds**. Both implementation hashes above remain unchanged. Independent conclusion unchanged.
