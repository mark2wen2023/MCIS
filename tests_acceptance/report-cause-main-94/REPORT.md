# Report cause-label integration on main94d5e38

Independent branch integration/report-cause-main-94d5e38 directly starts from
94d5e38c926fda232bb987b60fa9145e4bcf01a7. Source candidate01241b663e98b21807d08b7a9dc4affb1f0ec59a
has parent4585016; it was previously pushed to feat/report-recommendation-cause-provenance.
This combination does not change that original branch or main.

## Preservation and documentation
Applied the exact source candidate delta excluding REQUESTS.md/ROADMAP.md. Both
documents retain the entire latest-main bytes followed by the exact candidate
append relative to4585016, without removing any history. All12 other candidate
paths are byte-identical except the coordinator acceptance REPORT.md, whose stale
no-push statement is corrected to record the subsequent original-candidate push.
Historical independent reviews describe their original reviewer actions and were
not rewritten to imply new review or new tests.

All2408 non-candidate tracked main files independently compared by the executing
agent remain byte-identical. This includes evidence/router.py,
evidence_intake/router.py and report_output/attachment_access.py, the copied-ZIP
permission contract and tests, and new expert research modules. See tree-check.json
and frozen hashes. No old full-tree snapshot replaces latest main. Source and
input contract logic are unchanged from01241b6. No cause/evidence resolver added.

## Actual tests on the complete combined tree
service/.venv/bin/pytest -q
 service/tests/test_report_cause_provenance.py
 service/tests/test_reports_w16_sources.py
 service/tests/test_reports_w162_access.py
 service/tests/test_report_bundle_attachment_access.py
 service/tests/test_reports_font_coverage.py

112 passed,2 failed in28.56s (tests.txt). The112 comprise5 new provenance tests,
12 report-source tests,80 report-access tests and15 copied-bundle download tests.
Thus both legacy evidence GET and new Intake download boundary tests, policy
revocation and registered/restored bundle tests run with the combined source.
These are local synthetic HTTP/SQLite tests, not production identity assurance.

Both failures are the original public-report font tests receiving403 on creation
with Investigator before font assertions. Clean detached latest main94d5e38
reproduces both:2 failed in0.89s (main-control.txt). No role-policy weakening,
fixture fix, skip or mock was introduced to hide them. Logs retain failure details;
only trailing whitespace normalized. This is not a green full suite.

## Review / release limits
The original candidate had an independent17-test review on its older parent.
That is not independent review of this new combination. Only one development line
was used; no subagent was started. This branch is for the coordinator's independent
review, not merge approval. No merge or deployment performed.

Cause labels remain unresolved, Draft and explicitly unverified. The citation
opens the current recommendation register, not a historical revision-pinned source.
Existing saved-report text is a snapshot; safe report+recommendation archive remains
blocked. No actual model, HFACS/.NET, AIS, browser or visual layout run. Download
permissions are retained, not an SSO upgrade. Long-lock/memory and other prior
limitations remain. No software installation or protection bypass.
