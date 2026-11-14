# Issue directory independent integration review

Backend host list authored by read_resume, independently reviewed/tested by client_review. It uses only the existing authorized issue-list route, with before/after scope/auth checks and strict bounded minimal summaries. Independent21 plus previous47 host tests passed. No actor credentials or source content projected.

UI/model/hostPort authored by stored_ui_review, independently inspected and tested by read_resume. Review requested two fixes: prohibit history refresh while nonempty draft text exists (the old error path could clear that text), and retain known history baselines when returning to previously opened cards. Implementer added both guards and context-local knownCards. Independent issue-directory-review.tsx passed after final changes: list→open requires full read, draft blocks refresh/new-card, two separate cards exist, same-card and cross-card reopening refuse a regressed history, and a delayed old-context list is ignored.

The directory summary is not authority to append and cannot initialize an existing card at revision0. A failed read keeps editing blocked. Navigation is forbidden during unknown writes so it cannot silently abandon an idempotent retry. Context changes invalidate outstanding responses but cannot undo committed operations.

Runtime boundary remains React/HappyDOM with trusted synthetic host, not actual browser visual/layout testing, persistent user storage, production authentication or deployed workbench. No LLM/expert review consensus claimed.

Final frozen full related backend regression: **307 passed, zero skipped**,160.81s,one existing warning. Command: `PYTHONPATH=issue-journal/service MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh mcis-work/service/.venv/bin/pytest issue-journal/service/tests/test_issue*.py issue-journal/service/tests/test_identity_http_trial.py issue-journal/service/tests/test_trial_catalog*.py issue-journal/service/tests/test_web_demo*.py -q`. Includes new list22 checks; totals overlap previous suites.

Final UI implementation24 plus existing DOM29/source24/pins22/host15/main workflow and strict TypeScript all passed. Independent directory-review test passed on final hashes (same-card and cross-card baseline protection). Actual fictional host chain discovered and reopened five-entry card then appended sixth after full read. Frozen product hashes match implementation/independent reports. No unresolved blocking finding in this slice. CI not asserted.
