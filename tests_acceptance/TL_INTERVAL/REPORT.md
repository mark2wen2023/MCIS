# TL-INTERVAL implementation record

Base: main `3aba2bf03e393909c611489ae573a887087637ac`. Native subagent implementation, not a Codex application task.

## Implemented
- Inclusive interval intersection now uses an explicit null check: an event spanning negative relative seconds through `endTimeSec=0` is present at the epoch.
- Reject reversed/nonfinite query windows with 422.
- Reject missing/nonnumeric/boolean/nonfinite or reversed new event time ranges, including excessively large integers and UTC overflow, before persistence/audit.
- Equal endpoints and null/missing end retain point-event semantics. Negative relative seconds remain supported.
- Existing UTC conversion and display-timezone metadata unchanged. Source labels/evidence IDs and `presumptive`/`confirmed` flags preserved verbatim. No credibility determination.

## Local verification
`PYTHONPATH=timeline-interval-line/service mcis-work/service/.venv/bin/python -m pytest -q timeline-interval-line/service/tests/test_timeline_intervals.py timeline-interval-line/service/tests/test_cases_timeline.py`

28 passed in 6.86s (22 new parameterized cases + 6 existing). HTTP TestClient and temporary SQLite only; not browser, CI, core integration, deployment or live model testing. Synthetic records are explicitly labelled fictional, not presented as public accident/model evidence. Zero LLM calls.

Initial runs failed while materializing the isolated baseline because report inputs were absent then copied with an incorrect report checksum. Recovered exact inputs matching the existing YANGZE seed SHA256; no source/seed production edits. Initial new tests also used an invalid evidence ID format (`E-01`), corrected to existing-contract `EV-001`; all tests retained.

## Boundaries
`endTimeSec` means duration, not epistemic uncertainty or a clock-offset estimate. No time correction/inference or new uncertainty schema. Existing invalid historical intervals are returned unchanged on unfiltered reads; not silently repaired and still need a separate reviewed cleanup UX. No new source-access enforcement or authentication is claimed: existing timeline policy behavior remains. No automatic fact confirmation or source existence validation added.

Independent review completed: 37/37 tests (22 new + 6 existing + 9 independent), reviewer 10.91s; implementer combined rerun 9.64s. See INDEPENDENT.md. Implementation frozen SHA256 `4c334170edc25ab4ab35a8ac00caeb114c72f26dc799b33d22184db51c21bd62`.
