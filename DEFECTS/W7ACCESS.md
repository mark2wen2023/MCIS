# W7ACCESS independent acceptance — 2026-11-12

## Final ruling
**PASS for the scoped recommendation/consultation original-content fail-closed repair. No blocking defect found.** The inspected/final implementation matches all 9 entries in `logs/W7ACCESS-impl-hashes-frozen.txt` before and after acceptance. Normal authorized PR review/CI/merge may proceed after rechecking the exact final remote tree and any concurrent archive integration; this document does not itself merge or deploy.

## Independent tests
`tests_acceptance/W7ACCESS/test_content_boundary.py`: **27 passed**. Temporary synthetic-only database, no real incident reports/model/network:
- Default non-lead role matrix for list/detail/board/history/consultation; no original sentinel returned.
- Stored null/list/incomplete policy fails closed rather than becoming defaults.
- Recommendation-only, consultation-only and orphan-audit-only package detection without interview/report rows masking the result.
- Semantically equal default policy with reordered/pretty-printed JSON round-trips for all three package kinds; non-lead readers remain denied after restore.
- Package-supplied authority cannot authorize Investigator; lead receives 422 for unsupported policy; no Case/AccessPolicy rows or blob files left behind.
- Source custom policy returns 409 before export audit; unrelated empty legacy package remains compatible.
- Structured/raw audit markers, real database filtered/paginated raw-marker mismatch, orphan protection.
- Consultation comment mutation denies unauthorized actors without audit changes.
- Eight concurrent real SQLite recommendation writes terminate successfully without deadlock; chain remains valid and requests after committed revocation deny. Existing test below additionally covers held read versus concurrent revocation ordering.

`tests_acceptance/W7ACCESS/test_workbench_synthetic_regression.py`: **33 passed**. Imports unchanged W17 workbench assertions and overrides only `app` to seed synthetic Lily/Mary, not real reports.

## Existing regression rerun
**257 passed** across:
- `test_recommendation_content_access.py` (includes all roles/states, reads/writes, errors/no-store, held read/revocation ordering, non-SQLite rejection, raw workbench classification).
- `test_recommendations.py`.
- `test_reports_w162_access.py`.
- `test_interview_access_w52a.py`.
- `test_archive_export_safety.py`.
- `test_manual_interviews_w52b.py`.

Logs: `logs/W7ACCESS-independent.txt`, `logs/W7ACCESS-independent-workbench.txt`, `logs/W7ACCESS-independent-regressions-final.txt`, `logs/W7ACCESS-independent-freeze-check.txt`.

## Test-development/limitations disclosure
An initial independent run had two fixture construction failures (generic repository helper cannot write a stored JSON null; existing synthetic recommendation status was Responded rather than Draft). The fixtures were corrected; no implementation change. Initial broad regression yielded 206 pass/33 setup errors because original workbench fixture loads absent real report files; replaced only test app setup using the synthetic adapter above, all 33 original assertions then passed. Original log retained.

One upstream TestClient deprecation warning occurred. No full-product/Unity or browser regression was attempted because this repair changes no UI. HTTP route behavior was exercised through TestClient backed by real temporary SQLite databases, not a production server. Tests do not establish production authentication, complete redaction, provenance truth, CAS/idempotency, perfect backup compatibility, non-SQLite concurrency, or prevention of already-delivered client copies. W7.4 UI remains outside this acceptance; no W11/deployment/publication action was taken. Reviewer changed only acceptance tests and records.
