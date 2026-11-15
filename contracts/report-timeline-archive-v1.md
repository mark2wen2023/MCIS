# Bounded report and timeline archive candidate

MCIS-MCASE **1.4.0** requires working-records/backup.v1.json with MCIS-WORKING-RECORDS version1, plus timeline/records.v1.json. Existing1.0–1.3 meanings do not change. Unknown versions, missing/mismatched extension, v2 track-history or unknown business state reject; older readers must reject1.4 rather than silently drop events.

Timeline member: exact `{format:"MCIS-TIMELINE-RECORDS",version:1,caseId,events:[{key,createdUtc,updatedUtc,doc}]}`. At least1 and at most256 rows; UTF8 canonical bytes bounded by existing16MiB member/archive budgets. Doc follows timeline-event schema; key equals unique eventId, caseId equals enclosing case, timestamps parse as UTC, utc equals the existing timeline API sim_to_utc(caseEpochUtc,timeSec) result (millisecond truncation; preserve original timeSec, do not round/rewrite the stored document), finite endTimeSec is absent/null or >=timeSec. Evidence and vessel references must exist in this same package; duplicate evidence references reject. Preserve all original documents, source labels, flags, created/updated values and audit lines. Imported confirmed flags are unverified historical claims, not new approval. analysis/timeline.json is a checked mirror `{events:[doc...]}` in extension order, never an independent authoritative source.

Cases with nonempty timeline select1.4, including timeline-only cases: an otherwise empty working-record-v1 envelope accompanies the exact timeline rows. Timeline-only exports must not select1.0 because that importer refuses nonempty timeline content. Working-record v1 without timeline remains1.2. Working-record v2/track source history plus timeline is explicitly unsupported. Empty timeline extension rejects. Full-content authorization before reads and under existing reserved SQLite write transaction, including timeline/evidence/audit restrictions, remains unchanged. Unknown tables, conflicts, recommendations, consultations, COLREG and agent states remain whole-package refusal even without citations.

Importer validates before mutations, then restores timeline rows in the same database transaction as case/report/history and existing staged filesystem publication. Rollback tests cover injected failure; no cross-filesystem crash-atomicity claim. Original source packages and import audit/provenance remain preserved and inactive. New1.4 package artifacts are recognized as historical bytes on subsequent export without executing nested archives. Summaries retain existing working-record-v1 counts; outer packageVersion1.4.0 distinguishes added timeline support (no new UI wiring in this candidate).

Reference closure validates identities and available bytes via the existing archive validators; it does not establish source truth or authenticate role headers. Real SSO, concurrency performance, long-lock and memory limitations remain. No deployment authorization.

For outer1.4.0 only, this contract supersedes working-record-archive-v1.md §12.1 timeline_events refusal and its older historical-version enumeration. All other refusal/closure rules remain. Old clients currently reject1.4.0; this candidate is API-only and does not claim workbench/browser support. Historical confirmed flags retain existing listing/filter behavior; no new UI historical-status marker is introduced.

### Web alignment candidate

The descendant frontend candidate accepts1.4 only with working-v1 (and optional valid HFACS), binds receipt version/counts to its preview, and labels timeline scope separately. Other combinations remain server-rejected. Existing unknown-write and identity-change behavior is unchanged. Old clients still reject1.4. Rendered-browser acceptance is not implied by API or static-render tests; see the descendant QA record.

### Current-main bounded API candidate scope

This branch reuses only the backend profile on main94d5e38. The frontend alignment
mentioned above belongs to another unmerged candidate, not this branch. Current
web still rejects1.4. Fresh ordinary tests are recorded in
research/trajectory/BOUNDED_TIMELINE_MAIN.md; no inherited security/browser results
are claimed as current acceptance.

### Latest-import origin candidate

The descendant described in `timeline-import-origin.md` adds a local derived origin
index and visible per-event notices. It supersedes the earlier statement that no
historical-status marker exists, without changing the1.4 member or event schema.
Original declarations remain unreviewed by import; no new review endpoint is added.
