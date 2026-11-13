# Protected current-result read validation

Base 904018c5fc7f8595ab4584be066c9ed6e623cfe0; isolated snapshot.

Primary initial11 + existing307 regressions:318 passed, zero skipped,63.86s.
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh enables the two existing
actual W2 paths (HTTP save and internal save). No new GET core execution.
Independent review:19 new tests + initial11 =30 passed, zero skipped,17.11s.
Final primary14 + independent19 =33 passed, zero skipped,15.85s.
Coverage overlaps; do not add all runs. Product unchanged across these runs.
Final added3 exercise changed source bytes/review flag/index digest ->409.

Command prefix: PYTHONPATH=protected-read/service mcis-work/service/.venv/bin/pytest
Final read files: test_protected_result_read.py test_protected_result_read_independent.py.
Regression files: test_identity_http_trial.py test_identity_http_trial_independent.py
 test_local_authority.py test_local_authority_independent.py
 test_internal_unreviewed_save.py test_internal_unreviewed_save_independent.py
 test_protected_app_closed.py test_protected_app_independent.py
 test_unreviewed_api_closed.py test_unreviewed_api_closed_independent.py.

Native implementation subtask and independent native reviewer, not a separate
Codex desktop app run. Local ASGI/SQLite, not production/socket/browser/IdP/LLM.
No deployment/merge. Default entry remains deny-all. Trial GET current results only,
not history activation or approved timeline. See contract and independent report.
