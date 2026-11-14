# Issue source-selection pins: backend implementation

Changed journal.py, http_trial.py, host_bridge.py. Entry/event/archive schemas unchanged. Optional top-level sourcePins contains evidenceId, sourceIncarnation (canonical UUID), sourceSha256. Supplied pins must uniquely and completely cover Entry.sourceIds; lists limited to20. Nonempty pins are normalized by evidenceId into operation digest. Legacy calls without pins preserve existing digest.

Within the same authorized SQLite transaction, a new append compares currently authorized source incarnation and SHA against selected pins before adding a row, and repeats current source validation before commit. Mismatch or source-integrity409 yields SOURCE_SELECTION_CHANGED and transaction rollback. Permission errors remain permission errors; unknown errors are not misclassified. Historical same-operation retry checks digest and current authorization first, returns historical success without reattesting old source bytes. Altering pins with reused operation ID conflicts.

Protected HTTP create/append accept optional sourcePins. Specific source mismatch returns409 with only {code:SOURCE_SELECTION_CHANGED}. Host sources now exposes incarnation alongside source hash; host save with nonempty sources requires pins. Host maps only that precise known409 to ISSUE_SOURCE_SELECTION_CHANGED. Other errors retain ordinary rejection/uncertainty. UI must match scope/request ID; snapshot pinning does not confer evidence approval.

Test coverage includes initial/final incarnation/SHA mismatches with zero committed rows, missing/duplicate/extra/unknown pins, original byte changes, historical replay after source changes, modified-pin operation conflict, concurrent same pinned operation exactly once, source403 not misclassified, HTTP sanitized409, and host discovery→pins→save. Existing source projection assertion updated to allow the newly required sourceIncarnation field; no other reviewer tests changed.

This slice's code and new tests share an implementer. Separate review remains required before publishing. No push, merge, deployment or production/browser login performed.

Final relevant regression: **87 passed, zero skipped, 58.17 seconds**, one existing deprecation warning. Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_issue_source_pins.py issue-journal/service/tests/test_issue_host_sources.py issue-journal/service/tests/test_issue_host_bridge.py issue-journal/service/tests/test_issue_host_bridge_independent.py issue-journal/service/tests/test_issue_journal.py issue-journal/service/tests/test_issue_http_trial.py --disable-warnings`.

Reviewed-at-test SHA256:
- journal.py `edfded5afe79e19f7473703736dfed5289ce2cad1e095c3bd171cf3b26b1816d`
- http_trial.py `494645db7c9700e40dca7e3ef8d162b461bae5ec33f93584adfe80e232cc7264`
- host_bridge.py `847916137d72deb6d388dd50b4f92ffabe9e7b9e6a2e2e94613ef942702b3874`
