# ECFC archival follow-up (design only, not implemented)

The manual ECFC slice does not allocate an archive version. Saving even an empty chart creates case-scoped current/audit/receipt state and blocks that entire case's .mcase export. This is deliberate refusal, not backup support. Use a separate explicitly synthetic case for ECFC demonstrations; do not modify the existing successful bounded-archive demonstration to imply ECFC roundtrips.

Do not simply add the three table names to an export allowlist: that would suppress the warning while omitting reconstructible history. A small-looking change crosses import, versioning, source access, receipt replay and aggregate-budget boundaries and needs its own contract plus independent two-service tests.

Required design before implementation:

1. An explicit supported extension/version, coordinated with other in-flight archive work. Preserve basic and existing1.1/1.2/1.3 semantics; reject unknown versions. No version is reserved here.
2. Exact current graph, every supported revision and full before/after document, original event text/hash, and original request metadata. Do not truncate history to the UI's latest50 summary or regenerate lost input/actor facts. Node and source references remain hypotheses and registered metadata only.
3. Current and historical source authorization, all raw-content policy gates and row/case/document binding at export, preview and commit. Archives are not identity authentication, signatures or verification of the actual evidence bytes.
4. Imported request receipts must be inert historical records. An old request ID must not be replayed as a current successful save, including multi-hop restores. New IDs continue graph/audit history only after rechecking the restored sources and current privileges.
5. Bounded structural/digest/core-version verification of the entire extension plus aggregate package capacity. Fail the WHOLE export/import on unsupported state, lost originals or excess budgets; no silent omission, invented timestamps, fabricated old confirmations or partial replacement.
6. Empty-target restoration only, no overwrite of a case or active request. Test graph+history+receipts together, other-case isolation, malicious input, interrupted commit, incompatible readers and repeated export/import/export across independent services.
7. UI can remove the blocking acknowledgement only once that exact supported path is implemented and independently demonstrated. A successful limited roundtrip still is not a universal backup or whole-product completion.

Deferred separately: expert confirmation, causal analysis, evidence authenticity, report/statistics linkage, quantities/end-time/ship-location attachment, automatic layout/dragging, Unity runtime cards, agent generation and professional/legal conclusions.
