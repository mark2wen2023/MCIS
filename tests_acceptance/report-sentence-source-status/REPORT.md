# Sentence modify provenance correction

ParentPR104 head88cc9fdc4ed59704a1777aa58b0e16e058cf9220, independent branch
fix/report-sentence-source-status. Main remains94d5e38. PR104 is still draft/open.
Visible ordinary CI route-classification completed SUCCESS on this aggregate:
https://github.com/mark2wen2023/MCIS/actions/runs/43757581648/job/132944941367
That single check does not establish full CI/protection or production readiness.
No previously denied protection query retried.

## Reproduced and corrected

Using actual public YANGZE22 report generation, LeadInvestigator test header,
ordinary PATCH and fresh temporary SQLite: replacing either textZh or textEn
sets source=Investigator but previously left sourceStatus=PublicReportExcerpt.
Initial4tests:2failed2passed2.13s, failures exactly on incorrect sourceStatus.
Coordinator separately reports persistence across application restart and whole
section control already Investigator. This is a provenance-label inconsistency,
not a demonstrated permission bypass or changed original report.

Two-line product fix sets sentence sourceStatus=Investigator in the existing
modify path. Entire-section behavior unchanged. No permission, schema, archive,
source adapter, citation or generated-text rewrite. New contract explicitly
retains citations as context, not proof rewritten text is an official quote.
Old stored reports and historical audit snapshots are not migrated or silently
rewritten. Their inconsistency remains historical until a legitimate edit.

New5tests cover zh-only/en-only replacement, saved GET, application reopen with
same SQLite, generatedText/citation/unchanged-language retention, before/after
review snapshots, a newly generated report still containing the original public
excerpt, confirm/dismiss no-text behavior, and whole-section control. Test wording
is explicitly synthetic; public excerpt is actual repository authorized-public
material. No LLM or original evidence modification. During test development an
incorrect assumption of top-level audit action caused2KeyErrors; corrected to
existing auditEvent.action contract, not a production response change.

Command(service/):

    ./.venv/bin/pytest -q tests/test_report_sentence_source_status.py tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_reports_w16_sources.py tests/test_report_cause_provenance.py

Final result below. Uses genuine application handlers/SQLite and ordinary audit
reads; no tampering, restricted historical-integrity/security or ECFC probes.
Not full CI or independent acceptance. Real browser/production identity/real
HFACS not tested. Previous333+1skip/190failures are historical evidence, not rerun.

## Separate limited PDF visual check on unchanged PR104

Before this fix, real create_app/TestClient generated an authorized-public YANGZE22
cn-msa bilingual draft and exported it via the normal report endpoint. No model
call or fake renderer. Output210390bytes,18pages, SHA256:
96e85702cb39198428d5f50c8349d6ce297d541c16bdf9fceba9499336f3b09b.
Font matches main blob102a717709c10b1ffcfdc4bb35fb335124319e85.

Local artifacts only:/tmp/mcis-pr104-pdf-visual/public-report.pdf, report.json,
public-report.txt and page-01/04/17/18.png. Not added to Git or uploaded.
pdfinfo and pdftotext -layout ran; extracted all18pages include DRAFT and
不作责任认定. pdftoppm -f N -l N -r130 -singlefile -png rendered pages1,4,17,18;
these four actual page images were visually inspected by developer.

Those sampled pages show legible Chinese/Latin text, draft/page/footer labels,
visible review/missing-data wording, two-column body and dense citation appendix,
without obvious missing glyphs or column overlap. Page4 places a section heading
near the footer with continuation on the next page; excerpt also retains a
standalone original page-number artifact and a figure caption without the source
figure. This is text-excerpt presentation, not reproduction of the original PDF.
These layout/content limitations were not fixed in the provenance-label change.
No full18page visual inspection, all templates/languages, link interaction or real
browser verification. Four-page developer sampling is not independent PDF approval.

Final selected91passed28.33s,0skips/0failures. Includes5new tests; not91+5.
Local before/after logs:/tmp/mcis-source-status-before.txt and
/tmp/mcis-source-status-after.txt; SHA256 recorded alongside. New code remains
local candidate, no push/main merge/deployment or changes to PR104 in this task.
