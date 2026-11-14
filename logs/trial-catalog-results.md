# Protected catalog final verification

Base859289b8fd99e0d2b163a8193e68ac7ce4b0b234. Isolated native implementation and
independent reviewer; no separate Codex application executor claim.

Initial primary10pass/1fail found missing-case409 versus unauthorized403; initial
catalog authorization exceptions normalized403. Independent later actually reproduced
expiry during final load_case materialization returning200; response construction
moved before final reauthorization. Final product hashes in independent report.

Final independent25+primary11:36/36 zero skips,17.05s. Final affected regression
377/377 zero skips,102.91s, MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh.
Includes three actual W2 cases: prior internal save, HTTP save, extended catalog ->
HTTP save/read/replay/revoke. New single extended roundtrip separately1/1 in1.05s.
Counts overlap. Earlier pre-final full352 is historical, superseded by final377.

Regression comprises catalog main+independent, investigator_trial_roundtrip,
protected_result_read main+independent, identity_http_trial main+independent,
local_authority main+independent, internal_unreviewed_save main+independent,
protected_app_closed+independent, unreviewed_api_closed+independent.
Prefix PYTHONPATH=protected-catalog/service mcis-work/service/.venv/bin/pytest.

Actual SQLite/ASGI, not browser/network/IdP/LLM/production. Listing itself invokes
no core. Setup case/intake uses legacy fixtures, identity trusted host provisioning.
No complete browser login/workbench security, merge, deployment or full-system claim.
