# Saved observation -> report citation: integration gap

Exact base: 8b69e21fe01797d18d30366890e0d05eb04d5d52, inheriting frontend
6102b0b and backend58720e6. This is an unmerged stack; not current-main capability.
Only ordinary synthetic test and assessment added. No product/policy modification.

## Actual diagnostic

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_report_citation_gap.py

Developer run: 1 passed in0.40s. This passing diagnostic demonstrates a missing
feature; it is NOT a passing observation-to-report workflow. Temporary SQLite,
synthetic case and evidence registry, actual TestClient ASGI routes/JSON. No model,
original file or browser, no mocked report success. LeadInvestigator headers are
existing declared-role behavior, not proof of trusted production identity.

Sequence: register synthetic conflict; obtain registry receipt; change observation
text and save201; read revision2 with receipt association and SHA A; generate and
GET report201/200; append synthetic custody Change A->B; generate second report;
read conflict history again. Revision2 remains byte-for-byte JSON equal and
retains A. Reports cite EV-A, but neither cites C-01 nor contains the saved proposed
observation text. EV-A citation objects remain equal across reports. Thus no
report overwrite or loss was shown: the observation was never a report source.
The test does not assert quote authenticity, original bytes or all report content.

## Read-only contract findings

- reports/sources.py build_sections (~189) has evidence, COLREG, interview,
  recommendation and analysis sources; it does not load ConflictRow/ConflictRevision.
  ev_citation (~200) links an evidence item using ID/sourceRef, not a conflict revision.
- contracts/schemas/report.schema.json citation (~292) allows evidence, colreg-check,
  recommendation, interview-crosscheck, whatif, systemic; additionalProperties=false.
  No conflict revision/version/digest binding fields. Merely adding an href would
  neither represent nor validate the captured version.
- timeline/router.py (~164) exposes whole-conflict revisions with existing content
  and source checks; no single report-bound revision resolver contract exists.
  timeline/revisions.py history (~97) retains captured source values/unknown history.
- reports/service.py review_section (~172) preserves existing citations when prose
  is changed; writing an observation into report prose cannot create its provenance.

## Minimal safe next contract (not implemented)

1. Define a separate report citation kind for an investigation observation, with
   caseId/conflictId/revision/revisionSha256 and sourceReceiptId when present.
   Identify it as an investigator-recorded statement, never automatically a finding
   or confirmed report conclusion. Pin exact captured source bindings; do not use
   current registry SHA as historical evidence. Keep unknown legacy history unknown.
2. Generate from a verified, authorized captured revision within the existing report
   transaction; preserve full existing report/content and referenced-source checks.
   Current source version mismatch must be explicitly distinguished from historical
   reference integrity. No permission equivalence claim based solely on role names.
3. Define a resolver that selects the same case and exact captured revision, checks
   binding/digest and current access before returning it. No silent fallback to latest
   conflict, current evidence record or an unrelated ID. Provide UI displaying pinned
   version versus current ledger, not PDF/original-file validation.
4. Specify schema/backward compatibility and behavior for legacy reports, missing
   captured history, report revision/audit copies, export/import and sentence edits.
   Existing unsupported archive states must remain refused. Old reports must not get
   invented historical bindings. Acceptance must cover the complete intended read
   paths within the allowed scope, not substitute a current-item link for provenance.

These are missing product contracts/resolver/adapter, not a missing SDK or a proven
permission bypass. Adding the citation enum alone is insufficient. This turn cannot
claim complete historical-read consistency without those contracts and their
allowed acceptance plan, so no product wiring was enabled. No historically limited
report integrity/security or ECFC probes were retried. Browser, independent review,
production authentication and original verification remain untested. No merge/deploy.
