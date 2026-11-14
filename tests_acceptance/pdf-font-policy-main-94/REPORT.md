# PDF font regression identity repair on current main

Independent candidate branch fix/pdf-font-policy-main-94, direct parent
94d5e38c926fda232bb987b60fa9145e4bcf01a7. Only test code changed is
service/tests/test_reports_font_coverage.py. Its bytes exactly match the previous
e91e4cf candidate, whose old73fc800 parent is not carried into this branch.
Current main download protections and all product files remain unchanged.

## Intent and diagnosis
The original two cases are renderer regressions: actual project-font glyph
coverage, real PDF extracted Chinese text/maritime terminology, multiple pages,
DRAFT/non-liability markers on every extracted page. They must reach the renderer
under an allowed identity. Original Investigator requests are denied before report
generation: stored policy medical=Deny fails the full-content category gate;
FR-02 is additionally applicable. This is expected protection, not a font failure.

Prior fresh unchanged-main diagnosis retains2 failed in0.84s (baseline.txt).
It used this exact main, not the older candidate. Font Git blob independently
checked here as102a717709c10b1ffcfdc4bb35fb335124319e85 (font.json/scope.json),
not substituted with a system font. Policy or renderer was not modified.

## Test-only correction
Use explicit LeadInvestigator for the original two create/export paths; all
original substantive assertions and both case parameters remain byte-identical.
Add response detail on failed export status. Two new cases require Investigator
create403/FORBIDDEN/no-store with unchanged valid audit summary; after allowed
creation, Investigator PDF export403/FORBIDDEN/no-store/JSON rather than PDF,
unchanged audit summary and complete saved report. Default global H() unchanged.
Synthetic role headers test current policy only, not real authentication/SSO.
These refusal snapshots do not prove every database table or filesystem unchanged.

## Actual current-candidate regression
service/.venv/bin/pytest -q
 service/tests/test_reports_font_coverage.py
 service/tests/test_reports_w162_access.py
 service/tests/test_report_bundle_attachment_access.py
 'service/tests/test_report_output.py::test_real_single_render_bundle_and_legacy_archive[pdf]'
 service/tests/test_report_output.py::test_real_concurrent_renderers_and_legacy_export

103 passed in23.45s (tests.txt):4 font/denial cases +80 report permission cases
+15 copied-report-bundle download cases +4 real PDF/concurrent-output cases.
No skipped assertions, fake font/PDF renderer or altered business permission.
The output suites include their declared fault/race fixtures; real-render cases
remain genuine local renderer calls. This result is not full-repository success.

## Acceptance still needed
This new main-based candidate has not yet had independent review; old e91e4cf
review is not claimed as review of this branch. One development line only; no new
subagent. Requires coordinator independent review before further integration.
PR93 combination is not included or rerun here. No browser/visual-layout, real
model/HFACS/AIS, production identity or load testing. Public-report fixtures are
repository-authorized material; generated environments are temporary local SQLite.
No installations/downloads, remote push, merge or deployment in preparation.
