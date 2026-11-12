# W16.2 Full report content access boundary

This is a conservative access restriction, NOT redaction, verified identity, factual confirmation or a production authentication system. Header roles/operators remain self-reported. No policy is modified automatically.

## Gate
Both Investigator and LeadInvestigator may qualify. For full report content, ALL twelve existing categories (ais_sim, vdr_audio, testimony, personal, medical, report_draft, evidence_meta, timeline, colreg, recommendations, audit, agent_drafts) must explicitly be ReadOnly or ReadWrite. Content mutations and GISIS POST validation of supplied values additionally require report_draft=ReadWrite. GET report/GISIS exports only read content and append system access audit, so report_draft ReadOnly remains sufficient if every other gate passes. System access-audit writes are not content-edit permission. Any applicable field rule denies access because reports have no complete field-level redaction implementation. Malformed policy, unknown roles/categories/permission values or malformed/unknown rules fail closed. Absent stored policy uses the existing default; malformed stored policy does not fall back. Default Investigator therefore receives 403; default LeadInvestigator retains access. This intentional compatibility restriction does not change the default policy.

## Scope
All case-specific reports routes: list, create, colreg:draft, detail, regenerate, section review, report audit, report snapshot, PDF/DOCX export; case-specific report-templates and GISIS read/validate/export. Static templates without caseId and glossary stay public. Report lists and audit snapshots are full content, not safe metadata.

Indirect outputs: case audit listing and recommendation history must apply the gate if their actual returned rows contain Report category, report/gisis entity type, report.* action, or report-snapshot reference. Package export must gate before assembling files or appending export audit if the case contains report documents/snapshots or report-bearing audit events. No-report package behavior remains unchanged. Audit chain verification only returns chain metadata, not raw entries. Other narrowly filtered audit consumers (access-policy and case-metadata) do not return Report content.

## Transactions and responses
Protected reads use an explicit SQLite BEGIN IMMEDIATE before policy/data lookup. This reserves the writer slot even for read-only content requests: concurrent policy changes cannot commit while content is being prepared. It does not write business/audit rows. Mutations use the same transaction for policy, source reads, output construction and audit writes. This deliberately serializes protected content preparation; it does not promise revocation of bytes already delivered or protection after the transaction releases. Ordinary read-snapshot BEGIN alone is insufficient for a long export whose policy is revoked during rendering.

Gate before case/detail/source loads; denial is 403 FORBIDDEN with no case/content detail, no render, no files and no audit. All protected route success/error responses are Cache-Control:no-store. No field masking, source rewriting, role escalation, LLM, or completeness/readiness assessment is added.

## Review semantics
Confirmed/Modified are stored workflow states, not proven facts, authenticated signatures, legal findings or evidential sufficiency. Missing data remains missing even when a reviewer confirms text. This change does not alter professional templates or conclusions.

## Tests
Synthetic seed=False fixtures. Preserve original successful behavior assertions under qualifying Lead role and explicitly test default Investigator denial. Cover each category, field rules, malformed policy, read/write distinction, history/summary bypasses, same-snapshot and concurrent policy-update serialization, no-store and zero side effects on denial. Real-report fixtures are not read or fabricated.

Method references (context, not compliance certification): IMO MSC.255(84) §§2.12,22.2,23.1/23.3 describe report elements and investigation-record access/disclosure boundaries (https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255(84).pdf); MAIB How we work §6.3 describes draft factual/analytical consultation (https://www.gov.uk/government/publications/the-work-of-maib-explained/maib-information-leaflet). This engineering gate implements neither a complete legal disclosure decision nor professional fact verification.

Generic audit listing retains the existing audit gate and case lookup for non-report events; this is not a rewrite of all audit authorization. Report-bearing actual results (including raw line markers) trigger the full gate. Malformed/duplicate-key/nonfinite raw audit JSON is unclassifiable and triggers the full gate rather than being presumed non-report. This cannot classify arbitrary sensitive free text lacking any source/category marker.

Reproducible legacy compatibility selection: tests/test_reports_w162_legacy_synthetic.py reuses original synthetic W16 test functions/parametrizations with an explicitly seeded fictional Lily/Mary app created with seed=False, and runs old implicit-success operations with Lead. It does not change production roles or bypass the guard/renderers. Real/public-case tests are excluded. The old external-role template assertion is updated to deny case-specific metadata while preserving the same three static templates without a case.
