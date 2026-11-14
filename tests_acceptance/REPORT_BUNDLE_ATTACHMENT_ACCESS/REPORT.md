# Copied report ZIP access gate — 2026-11-14

Independent branch from254167e3e957784fd9d2d136a275731f33314d9b.
PR61 implementation files and all PR58/intranet files untouched. Scope excludes
recommendation, issue, timeline, dataset and semantic-support modules.

## Actual finding and implementation

Real report ZIP generation -> explicit opaque evidence registration was already
possible under8MiB, and .mcase preserves the complete ZIP unchanged. But default
Investigator, denied complete report preview, could retrieve this newly registered
ZIP via both evidence-intakes/{digest}:download and legacy evidence/{id}/content.
New regression assertions actually failed on both old-code paths (2 failed).

Added report_output/attachment_access.py and small integrations into the two live
byte-delivery routes. Recognizable ZIP (end-record detector) and leading-PK damaged
files require existing all12 full-content/no-field-rule permissions, regardless of
filename or category. No archive extraction or member reads. WRITE_LOCK followed by
BEGIN IMMEDIATE covers current policy/source reads, classification and Access audit.
Denied responses contain no bytes/success Access event. Restored history already uses
the full-content gate and is unchanged. No new persistent metadata or package version.

Compatibility tightening: all detected ZIP containers, including DOCX and unrelated
ZIPs, now use the full-content gate. General opaque registration remains possible;
registration does not grant download permission. Non-ZIP copies retain existing rules.
This is NOT general DLP, content classification, validated authenticity or production
identity: report content transformed into text/PDF/another container is not detected.
Do not describe this as closing all copied-content permission gaps.

## Executed verification

All cases synthetic; report renderer, API calls, SQLite, archive/export/import and
SHA checks are real local operations. No model or external service calls.

1. New15 tests plus existing evidence-intake/report-output tests:
   `cd service && .venv/bin/pytest -q tests/test_report_bundle_attachment_access.py tests/test_evidence_intake_w42.py tests/test_report_output.py`
   **155 passed,1 skipped,38.92s**. Skip: existing .NET SDK test unavailable.
   Covers both routes, permission downgrade reproduction/fix, leading-PK truncated,
   prefixed/empty/compressed ZIP, no decompression trap, misleading .zip plain text,
   current policy revocation, exact whole four-member report bundle registration ->
   .mcase -> fresh SQLite restoration -> full-gated original-byte download, historical
   receipt remains409/inactive. No attachment-name change in this branch.
2. Existing evidence and working-record archive regressions:
   `.venv/bin/pytest -q -rs tests/test_evidence.py tests/test_working_record_archive.py -k 'not test_report_versions_full_review_gisis_and_hfacs_coexist'`
   **46 passed,1 skipped,1 deselected,24.50s**. Skip requires .NET; deselected HFACS case
   was previously reproduced failing on pristine254167e with HFACS_CORE_UNAVAILABLE
   during PR61 work. It was not claimed newly executed or passed here.
3. Independent reviewer30 tests passed; see INDEPENDENT.md for details including
   all12 individual Deny checks, field rules, all-ReadOnly positive case, failure
   rollback and actual competing SQLite BEGIN IMMEDIATE lock refusal.

No UI change, browser test, C# pass, full-service/CI, production authentication,
model capability, deployment or merge claim. Generated bundles remain client-download
only until explicitly registered, with existing8MiB intake cap versus19MiB output cap.
Larger bundles are rejected, not truncated or automatically retained.
