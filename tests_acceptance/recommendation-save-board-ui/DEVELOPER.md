# Safety recommendation normal save → board reload (developer evidence)

Base: `833e8e532bef2ce35b26032fc5b0df5678086917` on top of test-only
`f7f4070bbc31756930662b29ad58d96c5680efd9`; product base
`9cc3ecee7251b6f19a739c14ce316740c048594e` combines UI `139f188` and PR104 `b4df823`.
This change adds tests and this record only. No product fix was needed by the selected flow.
Candidate: `test/recommendation-save-board-ui`; NOT main, not production, DO NOT MERGE without review.

## Gap and audited call chain

Existing `recommendation-form-save.test.cjs` replaces parent `onChanged` with a no-op;
`recommendation-missing-citation.test.cjs` uses a synthetic board with no HTTP.
Neither checks an actual saved recommendation returned by the service's board against the
real parent refresh callback and requested item selection.

- `recommendations/router.py`: create_rec → transition/_move → record_response → patch_rec;
  board and rec_history read back the committed data. Cause IDs here are explicit synthetic
  identifiers, not proof that a real cause exists or was verified.
- `recommendations/access.py:require_content` calls existing reports full policy check plus
  recommendations write level. No grants, policy rows or dependency overrides added.
- `cases/service.py:load_case` reads CaseRow; contracts.validate uses repository schemas;
  put_doc and audit.append write only the temporary SQLite session. Session exit commits.
- rec_history retains its audit/read checks and report/interview event filters. Inputs contain
  only the normal synthetic SafetyRec events; no report, interview or agent content is supplied.
- `RecommendationsPage.tsx`: query case/id → selected Detail → saveProgress → onChanged →
  board.reload/audit.reload. Test retains that parent callback, then rerenders with captured GET
  board data and checks the requested item, progress and report link case.
- `create_app(make_settings(tmp_path, seed=False))` initializes the complete ORM schema and
  existing triggers, including HFACS tables. No HFACS business/core invocation occurs.
  No demo seeding, report generation, source loading, file originals, listening server or model.

## Exactly one reviewed test selection

Run from repository root, using existing service venv and existing web node_modules (no install):

```sh
service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_recommendation_save_board_ui.py::test_synthetic_recommendation_save_reloads_requested_board_item
```

Developer result: **1 passed in 0.47s**, first execution. No skip/failure.
The Python node invokes `node tests/recommendation-save-board-response.test.cjs` in web,
passing only transient synthetic API captures on stdin. That child is part of this one test,
not an additional independently counted test. No broad suite or prior paused/refusal probe ran.

Real TestClient sequence: setup one schema-valid fictional case row; POST two synthetic
recommendations; POST issue and response for the explicitly selected second item; GET board;
PATCH progress to35; GET item/board/history. Assert status200/201, saved response equality,
unchanged response/history, unaffected other Draft item and progress audit before/after.

UI executes actual parent, Detail and useToast code under synthetic hook scheduling. It sends
the exact PATCH IDs/body corresponding to the captured service request, consumes the actual
captured response, retains parent onChanged, and replays captured GET board on reload. It
checks one board/audit reload, selection, saved progress, cleared submitted note, disabled
unchanged-progress save, success notice and report link case.

## Limits

This is developer validation, pending independent review. No live Node↔HTTP connection;
TestClient precedes UI captured-response replay. Hook scheduling/useLoad and ancillary UI
modules are substitutes; audit.reload is counted, not full audit-panel rendering. No browser,
real navigation/click, report-generated citation, report generation, race/denial/recovery,
production identity or permission assurance. Role headers exercise the existing test contract,
not trustworthy authentication. No source/version/real cause verification. No build rerun for
test-only additions. No real data, credentials or runtime databases are committed. Existing
archive protections and all unverified product boundaries remain unchanged.
