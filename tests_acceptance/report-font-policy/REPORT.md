# Real public-report PDF test prerequisite correction

Fetched main remains73fc8002868d9c6894b5fce6d03f7db690291bf6. PR82 OPEN at
79c935d1beb0169c06ebabbbc672af784df9c8ad; PR83 OPEN at
728d39097e22a735aba5bba11d935aabc4c9d387. Neither merged; their only code changes
are separate audit/consultation tests. See pr-status.json. New branch
fix/report-font-test-policy is directly based on main, without those candidates.

Baseline test_reports_font_coverage.py: **2 failed in0.82s**. Both fail on201
assertion after report creation returned403 for Investigator. Therefore baseline
did not evaluate font or PDF output; no font defect can be inferred from that
failure. The current service protects full report content under existing policy.

Only code change is this test module: use LeadInvestigator on authorized public
report generation/export. All original real-data status, Draft, production-font
glyph coverage, Chinese term, page count, per-page DRAFT/non-liability watermark,
review-needed/missing-data assertions remain. No alternate font or mocked PDF.
Actual repository production exporter produced PDFs in temporary test directories;
installed pdftotext25.03.0 extracted text. Real public reports already in repository
were used, no private cases/model calls. Local role headers are policy inputs,
not SSO or reliable production identity.

Two new denied-role scenarios cover both report cases: Investigator create403,
unchanged verified audit summary; authorized creation then Investigator PDF
export403/FORBIDDEN/no-store/JSON rather than PDF; unchanged audit summary and
full report document. Summary equality does not prove every database table or
filesystem entry is unchanged. Report/permission implementation is unmodified.

Self-tests **4 passed in3.16s** (after.txt). Related report access suite
**80 passed in12.57s** (related.txt). Independent acceptance saved separately.
No original assertion removed, no global fixture change, skipping, SDK installation
or fabricated core. No new product feature or archive-format compatibility is
claimed. PDF text/glyph tests do not certify visual layout or browser behavior.
Known HFACS two-failure environment gate and real-browser blocker remain; this
is not a green full suite or production security/performance acceptance.

No push, PR creation, merge, deployment or protection bypass in this task.
