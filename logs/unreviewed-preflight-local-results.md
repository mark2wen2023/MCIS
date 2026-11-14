# Local run results

Execution: native implementation subtask, separate native reviewer; not a separate Codex app.

- New tests: `MCIS_PREFLIGHT_REAL_CORE=<verified-wrapper> service/.venv/bin/pytest -q service/tests/test_unreviewed_preflight.py` → 19 passed, zero skipped, 10.96s.
- Selected regressions: same core setting; `test_unreviewed_preflight.py test_source_incarnation.py test_case_incarnation*.py test_registered_align_preview.py test_registered_parent_report.py` → 78 passed,3 skipped,35.26s.
- Skips are existing separate actual-core/public-report cases whose own opt-in configuration was absent. The new actual-W2 test ran, not skipped.
- Existing rebuilt W2 DLL SHA256 `657e99512fb9c42eb900fb1acb9bca5474ece49873b5ca74c78f3eb98355af41`, SDK8.0.428/runtime8.0.34. Single-executable wrapper invokes dotnet with this DLL and forwards arguments. Initial multiword core_cmd was invalid and produced503, then corrected wrapper passed.
- This suite is local temporary SQLite and synthetic evidence. No live LLM, browser, CI, deployment or complete saved-result lifecycle claim.
- Frozen implementation/contract checked separately. Independent report in tests_acceptance/UNREVIEWED_PREFLIGHT/REPORT.md.
