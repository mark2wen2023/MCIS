# Synthetic report review: service response -> parent callback -> SSR

Base: 9cc3ecee7251b6f19a739c14ce316740c048594e (UI + PR104 candidate). Test-only independent branch; no production changes. Developer evidence, pending independent acceptance.

## Reviewed call chain and scope

- main.create_app explicitly receives temporary Settings with seed_demo=False. Database/schema/blob directory are fresh pytest tmp_path resources; no default data directory. No app/client autouse fixture. Only schema resources are read for validation.
- Synthetic case and report are schema-validated before app creation, then inserted via put_doc into CaseRow/ReportRow in one setup session. This is a stored-fixture precondition, NOT report generation/import verification. No invented generation audit, policy row, evidence file, access override or source adapter mock. The citation explicitly remains unregistered and needsReview.
- GET report, PATCH section, GET saved report and GET audit use real FastAPI routes through TestClient, with existing LeadInvestigator role-header fixture and synthetic operator. reports.router.check_access -> require_content -> report_draft/audit gateway checks remain enabled. This follows current default policy, not trusted production authentication or new permission grants. No refusal request is made.
- PATCH holds existing WRITE_LOCK and DB session; review_section records before/after, changes source/sourceStatus, validates and persists the report. Its session commits on normal exit. This path does not call create_report/build_sections, analysis seed, public text, HFACS/core/model or original-byte reading. Existing SQLite trigger installation is app schema setup, not a write-refusal probe.
- Backend assertions inspect exact returned/saved section, original generatedText, inherited citations, untouched English, modified Chinese and revision before/after matched to returned audit.

## UI boundary

Python passes the actual synthetic GET/PATCH/GET JSON capture to Node over stdin, with no response fixture checked into the repository. Node drives actual ReportSession with a synthetic hook/router scheduler and replay adapter. Review payload/case/report/section are checked; the adapter returns the actual captured PATCH section (not a fabricated success body). Parent replaces the section, closes the dialog, emits saved notice and invokes refresh once. Actual ReportView is then rendered by React SSR from those parent props; assertions inspect Investigator source label, modified text, inherited-reference warning, citation and preserved original/revisions.

This is sequential captured-response contract replay, NOT a live browser-to-service connection. Ancillary startup list/template/GISIS/audit replies in the Node harness are synthetic. The React parent refresh/remount, full routes, failure/unknown results, authentication, visibility and production concurrent behavior are NOT tested. Fixture sourceStatus is CaseFields, not an actual public excerpt; no real accident data used.

## Execution

From repository root with existing dependency links:

    service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_report_review_service_ui.py::test_synthetic_sentence_patch_response_reaches_parent_view

First attempt failed in fixture schema validation before app creation: displayTimeZoneOffsetMinutes missing. Corrected synthetic fixture to include required 0; no contract/product change. Final same node: **1 passed in 0.51s**. Node subcheck passed inside that one pytest node; do not count as independent extra end-to-end tests. Node/esbuild/React reused existing installed packages, no installation. No build rerun (only tests/docs changed), full suite, paused/security/write-refusal node, model, browser, live service listener or original data access. No merge/deployment. Previous independent reviews and historical counts are not validation of this new test branch.
