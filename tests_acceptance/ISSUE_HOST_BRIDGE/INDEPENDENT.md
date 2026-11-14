# Independent Python trusted-host bridge acceptance

Final **25 passed, zero skipped, 19.14 seconds**: 18 independent + 7 main tests. One known Starlette/httpx deprecation warning.

Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_issue_host_bridge.py issue-journal/service/tests/test_issue_host_bridge_independent.py --disable-warnings`.

Verified actual Python ASGI + SQLite dispatch and separate Python stdin/stdout subprocess. Tests cover:
- socket.connect denied plus invalid HTTP_PROXY still allowing in-process save;
- fixed case generation/epoch precheck changes rejecting write (injected authority/load functions, not actual case database rebuild);
- close while committed response is pending suppresses late success, retains closed state; committed event is not magically rolled back;
- committed response loss returns sanitized uncertainty; identical operation retry has revision1, no duplicate;
- revoked write grant, mismatched case/context, injected URL/token/role rejected;
- foreign case/issue, approved status and invalid JSON response rejected;
- subprocess duplicate keys, NaN, oversized line, EOF with incomplete line rejected with fixed stderr;
- actual credential CLI arguments rejected before ready;
- real subprocess scope → save → read → EOF succeeds, no historical author IDs projected, temporary directory empty on clean exit;
- 101 supplied RPCs result in only 100 processed requests plus one ready message.

Earlier 23-test run passed before two subprocess tests were added. One intermediate run failed because the product protocol gained a required `profile` while the manually constructed subprocess message still used the earlier schema; test aligned and full suite rerun. This was protocol/test drift, not a product defect. Tests now frozen.

SHA256:
- host_bridge.py: `ebe46190006e565612d58b249c99d5d5586cbaa76e44531c46a75470d11e14fb`
- fixture_host.py: `84f3a08d8be29deede0298465894ecea1f06904920efdfccfe96bc363ba5a97a`

No remaining blocker within this isolated trusted-host scope. No production browser IPC, IdP/login, remote socket server, UI integration, real-case data, LLM or deployment validated by this review. The host is trusted and can inspect its own Python process memory; private attributes are not a defense against an adversarial host. Idle/overall deadlines inspected in source, not exercised as real 30/300-second wall-clock tests. Forced SIGKILL cleanup is not promised. Reviewer did not edit implementation or push/merge/deploy.
