# W17.1 Independent acceptance

## Results
- Independent API suite: **14 passed** after snapshot fix, including no-store headers on successful and denied responses.
- Real local FastAPI + Vite + headless Chromium: passed read-only policy view, current case URL/top-bar/page consistency, refresh clearing, delayed old-case response rejection, delayed old-identity response rejection, server-denied Public view, GET-only requests and no legacy-policy endpoint fallback. No page errors.
- Synthetic temporary data only. No deployment, publication, or implementation changes by reviewer.

## Defect and regression
Original independent API run: **13 passed, 1 failed**. A second database connection committed policy version 2 and its audit record between the endpoint's first and second reads. Response combined policy version 1 with version 2 audit, violating the promised single snapshot. The unchanged regression `test_policy_and_audit_are_one_snapshot` remains in the suite. Implementation owner added explicit SQLite BEGIN in this new endpoint only; retest passes.

Pre-review also identified missing-matrix UI label inconsistent with default-deny contract. Owner corrected it to `未配置（默认拒绝）` before final browser checks.

## API coverage
Role denial identical for existing/missing cases; per-case audit access denies Deny/Redacted/unknown/missing; default versus saved policy; successful/denied response cache prevention; no GET-created policy or audit rows; authorized missing case; exact action/category/entityType/entityId and case filters; zero/49/50/51 matching events, descending latest 50 and hasMore; consistent policy/history snapshot.

## Limits
Local role headers remain self-reported, not authentication. Displayed rules are configuration declarations, not proof of fully implemented redaction or legal compliance. This acceptance does not establish all legacy endpoints' authorization, production authentication, or system-wide concurrency correctness.

## Publication
Only this report, the API test, real-browser script, synthetic server fixture, and verified implementation hash list are intended for PR. Raw execution logs remain local; original regression assertions are preserved. No internal execution paths or raw environment logs are needed in the published record.

## Reproduction
```
cd service
PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W171/test_workbench.py
cd ..
MCIS_BROWSER_BIN=<existing-headless-shell> python tests_acceptance/W171/browser_real.py
```
