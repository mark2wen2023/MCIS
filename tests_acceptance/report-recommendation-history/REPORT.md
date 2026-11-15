# Recommendation historical binding candidate (author verification)

Base: PR95 head 0c182570107079794af048bfaf4e19a64b70dd63, parent
 a2dcc757c41afec029a450d02ad20abd304a4508. Complete main ancestor remains
94d5e38c926fda232bb987b60fa9145e4bcf01a7 (fetched 2026-11-15).
Independent branch feat/report-recommendation-history; original ac0dfe1 was pushed
for independent review. The audit-integrity follow-up is local pending review, not merged
or deployed. PR95/93/94 untouched. Independent acceptance pending.

## Implemented scope

Recommendation citation historicalSource captures generation-authorized original fields
plus case/report/time/source identity and canonical JSON SHA-256. The exact loaded source
projection is used, preserving missing versus null, whitespace and duplicates. Existing
href still opens the current register; UI explicitly separates it from expandable history.
PDF/DOCX reference metadata identifies captured time/digest vs current navigation. Full
historical fields are in report JSON/UI, not a complete evidence archive. Legacy reports
are unchanged and display history unavailable. Current read/list/export authorization is
rechecked; invalid v1 bindings fail 409, no current-record reconstruction. Source preview
build_sections callers have no persisted report identity and do not manufacture snapshots.

No schema migration/table or authentication/policy relaxation. Existing SQLite reserved
writer spans permission/source reads, snapshot/report/audit writes and commit. A synthetic
failure after audit flush rolls back all rows. Cross-connection BEGIN IMMEDIATE cannot
acquire writer during capture; later committed denial blocks old report reads. This is
policy transaction ordering, not production identity verification or cancellation of bytes
already delivered. Digest detects inconsistency; an attacker changing data and digest is
not cryptographically prevented. Snapshot fields are not verified cause/evidence links.

## Actual checks

- backend-selected.txt: 127 passed, 31.98s: history (11 at that point), existing cause (5),
  report sources (12), W162 access (80), attachment download (15), real font coverage (4).
- history-focused.txt: final 13 passed, 7.98s, adds cross-case and regeneration/missing-null.
  Real TestClient/temp SQLite with synthetic records; audit failure injected explicitly.
  A→B, digest/context tamper, missing/unknown binding, legacy, rollback, denial, concurrent
  writer, DOCX XML metadata and scope tests. No real model/SSO or private case.
- web-ssr.txt: report render suite including 4 new history assertions passed (152 total).
  This is React static markup, NOT a real browser. New text is escaped.
- web-build.txt: TypeScript/Vite build passed; existing chunk-size warning remains.
- compatibility-candidate.txt: 50 passed / 59 failed, NOT a full pass. Expanded group:
  test_working_record_archive.py, test_reports_w161_snapshot.py, test_reports_w16_direct.py.
  Exact-base comparison recorded separately below. No failing assertions removed.

Initial local tests exposed test-only fixture mistakes (invalid Observer role; expected
exception despite HTTP exception handler; typo import), corrected before the final runs.

## Boundaries

Only recommendation source fields are bound; other evidence/analysis citations are not
version-pinned. Fields duplicated per citation add storage/memory cost; no new total budget
or performance claim. Case archive with recommendations remains rejected; no migration or
restore promise. Existing recommendation-free archive compatibility tested in expanded
suite. Existing consumers accepting optional fields remain compatible; externally frozen
strict schemas need update. Report source hashes are consistency checks, not signatures.
Real browser/visual PDF, real models/HFACS/.NET, production identity/SSO, load performance
and external client acceptance are unverified. Current role headers remain self-reported.
Long authorization write locks are retained. No automatic retries or cleanup.

Exact base 0c18257 rerun: 50 passed / 59 failed, 38.79s. All 59 failing node IDs
match candidate exactly (asserted programmatically). Baseline log retained. These failures
remain unresolved; individual causes have NOT been fully diagnosed. Matching failed node
IDs do not establish identical root causes or full-suite success.
