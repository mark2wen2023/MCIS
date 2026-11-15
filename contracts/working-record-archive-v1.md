# Working-record archive v1 — second-review contract, NOT implemented

Status: B contract for second independent review, not yet accepted or implemented. Archive safety A remains operative. This document does not grant implementation or publication approval. W19/W12 work is independent; do not modify their tables or artifacts. No W11/ECFC scope.

## 1. Smallest restorable scope

Restore a NEW case with the SAME caseId: existing W8.5 basic case/vessels/tracks/environment/evidence/custody/raw audit, complete interview documents, complete saved report versions and operation snapshots, inert manual request history, optionally the existing HFACS extension. No merging, overwriting, reclassification, regeneration, legal validation or signature authentication. Existing signed/Confirmed/Modified flags are preserved historical workflow data, not new attestations.

This is a bounded supported-subset archive, NOT a universal case backup. Nonempty unsupported business state causes whole-package refusal even if no current report cites it. Export cannot silently omit a table merely because the old build_files did not serialize it. Before implementation freeze, enumerate current registered case-scoped tables and their authoritative serializers; fail closed for any populated case-scoped table outside the explicit allowlist. Operational intake receipts/source.mcase archives require the explicit treatment in §12–15, not silent exclusion.

## 2. Exact version combinations

| packageVersion | working-record member | HFACS member |
|---|---|---|
| 1.0.0 | absent | absent |
| 1.1.0 | absent | existing hfacs/backup.v1.json required |
| 1.2.0 | working-records/backup.v1.json required | absent or existing exact v1 member |

1.2.0 is emitted only when supported working records or their history exist. Never downgrade nonempty working records to1.0/1.1. Unknown versions, case variants, alternative namespace files, additional fields or incomplete combinations reject. Old service import explicitly rejects 1.2.0/working-records namespace before applying SQL, policy or blobs. Only the new bounded parser issues an internal validated capability bound to exact original bytes and caseId. Existing old readers/Unity are NOT guaranteed to reject or preserve extensions; only this version's restricted workflow is supported.

New packages use a single authoritative working-record member, NOT duplicate testimony/*.json copies. Legacy testimony members alongside1.2 reject to avoid conflicting originals. Legacy1.0/1.1 import boundaries are unchanged; absence of the extension must never be advertised as full report/interview recovery. Archive safety A remains the fallback for content that fails this extension's validation.

## 3. Exact member envelope

`{format:'MCIS-WORKING-RECORDS',version:1,caseId,receiptPolicy:'archive-only-on-import',interviews:[],reports:[],reportSnapshots:[],manualReceipts:[],importHistory:[],historicalArtifacts:[],lineage:{nodes:[]}}`.

Each interviews/reports/reportSnapshots entry: `{key,createdUtc,updatedUtc,doc}`. Retain original DocMixin created_utc/updated_utc strings exactly; validate parseable UTC without inventing times. Local SQL integer primary keys are not transported. doc is preserved structurally and with exact string/codepoint values, not rebuilt from rendered output. Existing report/interview schemas remain necessary but insufficient: archive adds strict fields/reference checks. Outer original ZIP bytes are retained by intake; database JSON serialization is not claimed byte-identical JSON whitespace.

- interviews: entire InterviewRow.doc, including caseId/recordId/interviewee/location/time/turns/sensitiveFragments/statements/crossChecks/signed/evidenceId/sourceSha256 and all schema-defined fields. Preserve questions/answers, UTF-16 spans, quotations, review data and legacy optionality. No fabricated start time, no re-signing, no rewriting source identity.
- reports: entire ReportRow.doc. Preserve reportId/familyId/parentReportId/version/templateId/lang/status/createdBy/createdUtc/isFictionalDemo/realDataStatus/sections/generatedText/reviews/citations/disclaimers/reportHref and every defined nested field.
- reportSnapshots: entire ReportAuditRow.doc with reportId (nullable for GISIS), sectionId, sentenceId, reason, beforeValue, afterValue, summary and auditSeq. Preserve orphan/GISIS histories subject to §5, not just snapshots returned by one report's latest audit API.
- manualReceipts: exact `{case_id,request_id,operation,record_id,request_digest,operator,role,receipt}`. receipt retains requestId/operation/recordId/beforeDigest/afterDigest/turnRound/appliedUtc. No original request body is invented or duplicated.

Global audit/audit.jsonl and custody JSONL remain full original lines, not reconstructed from truncated before/after summaries. Validate hashes/sequence and all manifest hashes/sizes. Agent audit is unsupported unless empty (§6).

## 4. Manual receipts: historical, not authorization

Export union of active and archived manual receipts with unique(case_id,request_id); duplicate IDs reject even if content happens to agree. Import all as append-only archived rows, NOT active replay receipts. Re-export preserves exact original receipt fields, including original actor strings and request_digest. Request digests cannot be recomputed from a current document or sorted receipt, and are not proof of sender identity.

Create/append must reject any archived requestId as historical-only; new requests use new IDs. Archive read/recovery uses current full-content/source authorization and original actor matching before disclosing metadata. It never reports replayed=true as an executed restored action. Missing current record is explicitly historical-target-unavailable; a404 never proves an operation did not happen.

Both new manual allocation and legacy create must reserve ALL active+archived record_ids, including orphan receipts. No ID may be reused for another document. Existing old record writers remain under their existing transaction and signed-record restrictions; no history migration changes sourceSha256 or enables previously blocked append.

Allow orphan archived receipts as retained history, not reconstructed documents. The current document may differ from last receipt.afterDigest because old writers legitimately changed it. Do not require a false contiguous receipt digest chain. Check operation/nullability/ID/role/hash/time shape and internal agreement, but do not claim a bijection to global audit: current receipts have no auditSeq. Duplicate/scope conflicts reject rather than selecting one.

## 5. Reports, versions, reviews and audit mapping

- Row key=doc.reportId; caseId matches envelope; unique reportId and (familyId,version). Parent graph is acyclic and same family/case, parent version lower; root parent null and root reportId=familyId. All referenced parents must be included. No requirement to invent missing versions or renumber existing versions.
- Each snapshot key is unique; auditSeq points to an included global Report event whose raw line snapshot_ref equals report-snapshot:<key>. reportId maps to event entity_type/entity_id; null reportId is GISIS and case entity. Event operation must agree with the snapshot shape and referenced section/sentence. A leftover report-snapshot reference without its snapshot rejects.
- All snapshot rows are retained, even if no current report references them. A snapshot with nonnull missing reportId rejects the whole archive in v1; preserve the database unchanged, do not invent its report or silently drop it. GISIS null-report snapshots are valid distinct history and require full before/after payload validation.
- Current report and embedded section/sentence reviews must reference included matching global event and full snapshot. Match action/operator/reason/target and beforeValue/afterValue under the existing review algorithm. These are referential consistency checks, NOT historical authenticity proof.
- Do not require snapshot afterValue to equal the current full report: reviews can target sections/sentences and later operations change content. Existing snapshots omit nested reviews to avoid recursive history. Do not reconstruct a full historical document from these partial shapes and call it an exact version.
- ReportRow documents and all snapshots are independent preserved payloads; no generate/review API is invoked during import. Existing schema permits arbitrary before/after objects, so archive must dispatch validation by known operation (generate/regenerate/colreg draft/review/export/GISIS validate/export). Unknown operation or unexplained snapshot shape rejects rather than treating arbitrary objects as safe.
- Current schema/manifest provides transport consistency, not tamper-proof pre-export storage. ReportAuditRow is not an independently hash-chained immutable ledger. Preserve this limitation prominently.

## 6. Source dependency closure, not only visible links

Current explicit report citation kinds are exactly:

| kind | v1 treatment |
|---|---|
| evidence | registered reference must resolve to same-case packaged evidence, canonical registered SHA, required bytes/hash and safe path; historical unregistered/missing stays marked, never promoted |
| interview-crosscheck | registered reference must resolve to included record AND exact statement/crossCheck identity using structured sourceRef/route; ambiguous duplicate statement IDs reject; include any associated evidence references |
| colreg-check | registered reference rejects: COLREG runs/annotations and dependencies are outside this slice |
| recommendation | registered reference rejects: recommendation/implementation/consultation state is outside this slice |
| whatif | registered reference rejects: adapter/scenario/seed dependencies not packaged here |
| systemic | registered reference rejects: adapter/core model dependencies not packaged here |

Unsupported kinds marked missing/unregistered may remain only as explicit unresolved historical citations; do not construct live entities or relabel as restored. Inconsistent registration/unregistered flags reject. Preserve href text only after verifying same-case route and supported ID binding; never follow external links during import. Exact route grammar is specified in §13.

Inspect citations in ALL report versions, generated/current sentences, embedded review before/after, complete operation snapshots and source-bearing interview crossChecks/statements, not just latest display. Missing reference arrays do not establish completeness. In particular case/vessel prose uses metadata with no citation; consultation-round prose has no consultation citation kind; both must be accounted for structurally.

Unconditionally reject nonempty timeline events/conflicts, COLREG analyses/runs/annotations, recommendations, consultation rounds, agents/drafts and agent audit, what-if/systemic scenario state, and all other unlisted business tables/artifacts. Explicitly inventory model registry plus blob namespaces before freeze, without reading real report sources. Do not traverse or implement W11. A case with any W11 state is outside this slice and must not be partially archived.

For interview sources, preserve historical doc exactly. Registered evidenceId must resolve same-case, visible to exporter, hash agree with sourceSha256; package raw evidence integrity remains independently checked. No source is allowed and stays no source. Legacy nonempty sourceSha256 without evidenceId may be preserved as explicitly legacy-unverified history; new append remains blocked. Unknown evidence IDs/hash mismatches reject; do not silently attach or correct them. Full text may contain personal/medical data, so source visibility is additional to full-content permission, not a substitute.

## 7. Permission and identity boundary

Export, preview, commit and recovery require existing investigator role plus all12 categories explicitly RO/RW and no applicable/unknown field rule, including audit/report/testimony permissions. Default Investigator is denied; default Lead qualifies. Export is a read of source content plus system audit; no automatic policy editing. Import is new-case administrative creation under separately explicit endpoint authorization, not permission copied from untrusted content. Package policy must equal current supported default policy exactly; custom policy rejects, never normalized.

Check all historical source visibility, not only current rows. Before new-case creation, evaluate caller against server-owned current default_policy(), all12 categories and fieldRules; never trust a claimed package role or supplied matrix. Existing case recovery additionally rechecks current policy and source access for all archived material before showing summary or receipts. Refusal happens before unsupported-state detail for unauthorized callers. Role/operator strings are local self-reported values, never authentication. Imported actor/signed/review status is unverified history, not a new reviewer decision.

## 8. Transactions and filesystem

Export uses one reserved SQLite writer snapshot with existing reviewed lock order; validate full closure/permissions before appending export audit or assembling deliverable files. Preflight the candidate archive for supported restore, append one export event, assemble/validate final bytes in same transaction; error rolls back that event.

Import validates strict bounded ZIP/JSON and semantic graphs before any mutation; uses new caseId directory staging, single database transaction for base/interview/report/snapshot/archived-receipt/optional-HFACS/intake rows, and existing filesystem publish/cleanup discipline. Collision in case, path, archived IDs or unsupported data rejects. SQL failure, file publish failure and post-flush failure roll back all new rows/files. Original package bytes remain intact. No overwrite, deployment, network fetch, raw media decoding, model invocation or report regeneration.

Retain existing32MiB compressed/64MiB expanded/16MiB member/2048 members, ZIP collision/CRC/encryption/path rules and strict duplicate/nonfinite/depth64 JSON rules. Working-member budgets:128 interviews,256 reports,1024 snapshots,2048 manual receipts, plus16MiB total member. These are engineering limits, not professional limits; exceed => whole refusal, never truncate. HFACS retains its existing stricter budgets/version/core validation.

## 9. Preview/commit/recovery summary

Retain existing package digest-bound preview/commit mechanics. Add `workingRecordsExtension:null|{version:'MCIS-WORKING-RECORDS-1',interviewCount,reportCount,reportSnapshotCount,manualReceiptCount,receiptMode:'archive-only',identityMode:'unverified-self-reported'}`. packageVersion and summary must agree with exact validated member. Warnings explicitly distinguish unresolved historical sources from restored registered sources. Legacy historical intake receipts without new fields require explicit compatibility rules, not guessed counts.

## 10. Synthetic acceptance matrix

1. End-to-end basic+manual create/append+old legitimate edit+two report versions+sentence/section review+export+empty database import+reopen+re-export: exact document strings, timestamps, version graph, snapshots, original audit lines and archived receipts match (only explicitly new import/export audit entries may extend chain).
2. Optional HFACS coexistence; basic1.0/HFACS1.1 unchanged;1.2 exact combinations; unknown/missing/extra namespace/duplicate testimony reject.
3. Historical receipt cannot replay; changed current digest allowed; orphan receipt preserved; new/old create cannot reuse archived recordId; actor mismatch/current denied recovery reveals no history.
4. Six citation kinds, unregistered/missing consistency, duplicate ambiguous IDs, cross-case source, hash mismatch/missing bytes, history-only citation, citation-free consultation state, populated unsupported model table => explicit whole refusal.
5. Parent cycle/missing parent/duplicate version; missing snapshot/audit ref; false auditSeq; review mismatched action/operator/reason/values; orphan GISIS and report snapshot policy; corrupt global chain; unknown snapshot shape.
6. All12 permission matrix/field rules, default Investigator deny/default Lead, source restricted, policy change before commit/recovery, unauthorized response/no-store/no-detail; no external calls.
7. Oversize/malformed/duplicate/nonfinite/Unicode/ZIP path and manifest failure; case/path collision; DB/file/after-flush failure: no partial base/docs/receipts/HFACS/intake/blob or export audit.
8. Concurrent export/save coherent snapshot; preserved lock-order regression; retry same import digest does not duplicate rows; complete source.mcase integrity check.
9. After restore, signed records remain immutable; original spans/quotes remain exact; generated text and Confirmed/Modified are historical workflow labels, not independently verified facts.

## 11. Settled scope and freeze condition

Non-null orphan report snapshots reject; valid null-report GISIS snapshots are preserved. Legacy sourceSha256 without evidenceId is retained as explicitly unverified history without changing the original doc or lifting append restrictions. Missing/unregistered citations remain unresolved in UI, never promoted. DocMixin UTC strings are preserved exactly if parseable; invalid timestamps or unknown fields reject.

Operational history follows §12–15. All source receipts are inactive after restoration. No unknown-version history package is supported. Exact envelope, row policy, counts and byte caps in this document are the contract under review, not deferred implementation choices. Only independent review acceptance permits implementation freeze. Baseline is approved main80fad29b, including separately authorized PR32; uncontracted new case-scoped data rejects instead of being silently omitted. W11 remains outside scope.

## 12. Operational history and original bytes — required refinement

The target includes ordinary W4.1 evidence-intake cases, not only hand-built empty demos. No imported credential-like receipt becomes a destination replay credential. All original audit/custody lines and their detail fields remain byte-exact; do not rewrite embedded operators, digest bindings, prefixes or provenance.

### 12.1 Actual inventory on reviewed main

Registry alone is insufficient: reports register through router imports and package intake declares its model in router.py. Source inspection (no real evidence reads) found:

- Basic allowlist: cases, vessels, track_points, evidence_items, custody_events, audit_events, environment_observations, access_policies(default only).
- Working records: interviews, investigation_reports, report_operation_snapshots, interview_request_receipts; new archived manual/index/artifact tables are explicitly part of this extension.
- Existing optional HFACS: hfacs_worksheets, hfacs_worksheet_audit, hfacs_worksheet_requests, hfacs_archived_requests.
- Operational history requiring preservation: package_intake_receipts plus per-case `_package_intake/source.mcase`; W4.1 evidence receipts are derived from custody Register.detail beginning `MCIS-EVIDENCE-INTAKE/1 ` and `raw/evidence-intakes/{digest}/source.bin`, NOT an independent receipt table. Evidence metadata/doc stays exact.
- Reject if case-nonempty: sim_commands, agent_drafts, timeline_events, timeline_conflicts, colreg_analyses, recommendations, consultation_rounds and any subsequently registered non-allowlisted case-scoped table. Do not inspect stopped W11 artifacts; current registered state is sufficient to refuse unsupported populated tables, not an excuse to traverse that work.
- knowledge_cards/knowledge_audit are cross-case global library state, explicitly excluded from a single-case archive. Never call this a whole-system backup. Referenced global knowledge cannot be represented as restored local source; unresolved or unsupported references follow the closure rules.

Before coding against later main, re-enumerate imported ORM metadata AND source-declared tables, inspect SQLite table schema for case_id ownership, and check authorized per-case artifact directory paths. A populated unknown case-scoped table rejects; unknown non-case ownership requires classification, not unconditional copying. Every per-case file must be an approved evidence object, approved current operational artifact, approved inert historical artifact, or explicitly documented reproducible cache. Unknown nonempty files reject; symlinks/special files reject. Do not access unrelated case directories.

### 12.2 Inert import-history entries

importHistory entry is exactly `{kind,caseId,key,createdUtc,updatedUtc,metadata,sourceArtifactSha256}`; kind is `package-intake` or `evidence-intake`. Package metadata preserves the full original receipt doc and row key/timestamps, sourceArtifactSha256 references exact source.mcase and is required nonnull canonical SHA for package-intake. For evidence-intake sourceArtifactSha256 is exactly null: source.bin remains at its original evidence relativePath and is not duplicated in historicalArtifacts. Evidence metadata preserves exact custody seq/line reference, evidenceId, requestDigest, original parsed binding and source-byte SHA; no fake row timestamps (createdUtc/updatedUtc null for this derived representation). Validate derived metadata against original Register.detail and original evidence path/hash rather than trusting duplicate fields. Unknown receipt profile/version cannot be activated; supported historical package versions are limited by §15.

Import history is stored append-only and never consulted as successful replay. A separate archived-evidence-intake digest index keyed by (caseId,requestDigest), plus immutable reserved evidenceId, is populated atomically before exposing the restored case. Existing evidence intake load_receipt must check this index after current permission checks and BEFORE scanning custody records. Every existing GET recovery/by-evidence and POST commit/preview-to-commit route that uses load_receipt returns explicit historical-only409, not replayed success. Same request digest cannot be reused for a new upload; no server nonce workaround. Imported evidence/request identifiers remain reserved against legacy and new allocation even if current evidence records later disappear.

GET `/api/v1/cases/{case_id}/archive-history/evidence/{evidence_id}/content` serves historical raw evidence through a dedicated history-source endpoint that leaves historical bytes unchanged but appends a new Access event with current case/evidence/full-content permission checks, safe-path/hash verification and no receipt activation. It returns original bytes as attachment/no-store, not active replay metadata. The existing `/evidence/{id}/content` is NOT assumed equivalent: current implementation lacks explicit no-store and reserved permission snapshot. For archived-marked evidence only, the old content route must perform current full-content authorization first and then return historical-only409 before reading bytes or appending custody. UI routing alone is not a security boundary. Other non-archived legacy content behavior is outside this change. Response is raw bytes only with Content-Disposition attachment and no-store; metadata is not an executed receipt. Acquire existing WRITE_LOCK first, then BEGIN IMMEDIATE, require full-content all12 RO/RW/no applicable field rule plus current evidence visibility; verify original file hash and prepare response under the same authorization snapshot, then append an ordinary new custody Access event under the same WRITE_LOCK→BEGIN order. Commit successfully before returning/transmitting bytes. Do not use BEGIN→append_custody because custody still obtains WRITE_LOCK and would invert export locking. On denied/hash/path/read failure append no success event. This does not revoke already authorized bytes. New access audit is allowed under ordinary access semantics; original custody lines remain unchanged.

Manual/HFACS/package imported request IDs/digests likewise remain inactive. Destination package intake creates ONE new active receipt for the current outer package; preserved source package receipts are only history. On a subsequent export, that current receipt and its exact current source.mcase become historical entries in the next archive. Current and historical entries with matching kind/key must have identical payload/bytes or reject; deduplication cannot silently select conflicting histories.

### 12.3 Opaque original package artifacts and finite growth

historicalArtifacts entry exactly `{sha256,sizeBytes,relativePath,mediaType}`; bytes are at `history/artifacts/<sha256>.bin`. Each artifact is content-addressed, manifest-listed and exact bytes, not reconstructed or recompressed internally. Every nonnull importHistory sourceArtifactSha256 resolves to exactly one included artifact object; multiple history entries may reference that same SHA. All artifacts must be referenced by importHistory and one lineage node; missing or unreferenced artifacts reject, with no ancestor exception. Lineage is the separate exact object below, never inserted into original receipt metadata. Never infer provenance by executing inner packages.

Previously saved source.mcase, including its embedded older archives, is retained as opaque bytes. Do NOT recursively extract to disk, execute/import nested contents, follow paths or activate receipts. Perform only the bounded read-only manifest/case/hash checks in §15. Only historical source packages with supported packageVersion1.0.0/1.1.0/1.2.0 are accepted; any unknown inner version rejects export and import of the whole outer archive. The bounded read-only checks in §15 do not execute inner content. Exact duplicate bytes share one artifact by SHA, but a newer package containing older bytes is not considered identical and cannot replace its ancestor.

Finite budgets: maximum8 external lineage DAG levels (not verified opaque nesting depth),32 historical artifacts,2048 import-history entries; each artifact<=16MiB under existing member limit, combined expanded package<=64MiB and compressed<=32MiB. The total includes BOTH current evidence and all original historical bytes; no exemptions for nested ZIP compression. A prior source.mcase larger than16MiB, lineage beyond8, or any aggregate overflow causes explicit whole-export refusal. Multi-generation growth is real and may exhaust the budget quickly; do not discard oldest history, recompress source bytes, truncate, or claim unlimited archival support. These constants are part of this review contract and are not yet implemented. Original3-library round-trip test must compare every retained artifact SHA and raw bytes at each generation.

### 12.4 Additional required tests

Ordinary evidence intake→manual evidence binding→report→archive→empty destination: raw bytes/doc/custody line equal, imported load_receipt GET/by-evidence/POST returns historical409, protected historical download works, unauthorized cannot learn the digest, same digest upload cannot reactivate, reserved evidenceId cannot be reused. Active destination receipt for the outer import succeeds independently. Export again to a third database: retain both generations' source.mcase bytes and original receipt metadata, preserve all inactive indexes, no accidental replay. Failure while inserting any inactive index/artifact metadata rolls back all case rows/files. Unknown inner or outer package version rejects; artifact missing/hash mismatch/reference conflict/generation/size overflow reject without deleting existing history.

## 13. Exact relational and URI rules for review

All keys described as identifiers are nonempty Unicode-scalar strings bounded to256 codepoints unless their existing schema is stricter; filesystem case/key identifiers additionally use existing safe path/ID grammar. No unpaired surrogates, duplicate JSON keys, unknown object fields, nonfinite numbers or booleans masquerading as integers. Lists retain original order; validation never sorts historical doc arrays to manufacture agreement.

Envelope has exactly the eleven fields in §3 including lineage (format,version,caseId,receiptPolicy,interviews,reports,reportSnapshots,manualReceipts,importHistory,historicalArtifacts,lineage). version is integer1. All row keys unique per collection; every document's case/record/report identity must match its envelope/key. Manual receipt key unique across active+archived, importHistory unique(kind,caseId,key). Duplicate identical rows are rejected, not silently coalesced. Historical artifact SHA unique and relativePath exactly history/artifacts/<sha>.bin, mediaType exactly application/octet-stream, sizeBytes integer0..16777216. SHA lowercase64 hex; file bytes must match exactly. Only export's explicit identical-byte artifact deduplication permits multiple refs to one object.

lineage is exactly `{nodes:[{artifactSha256,parentArtifactSha256s:[]}]}`. Node SHA set equals historicalArtifacts SHA set; each parent list contains distinct existing node SHAs, no self-reference. Every node is referenced by at least one package-intake importHistory entry. Graph is acyclic, maximum longest path8 nodes, maximum32 nodes. No dangling parent, duplicate node or unreferenced ancestor. On re-export, add the prior active source.mcase node whose parents are the tip nodes in its preserved external index (nodes not referenced in any other node parent list); keep original ancestor nodes unmodified. Conflicting parent assignments for same artifact reject. This records the protocol's external declared DAG only: opaque packages are NOT recursively opened, so it cannot authenticate their true embedded depth or undeclared history. Display this distinction; budget refusal must explicitly explain a source.mcase up to32MiB from an older intake may exceed the16MiB historical-member cap.

importHistory metadata exact tagged shapes:
- package-intake: metadata is the original package_intake_receipts.doc under its known supported profile/version, unchanged; key equals original sourceSha256 and sourceArtifactSha256, caseId and byteLength agree with artifact. createdUtc/updatedUtc preserve original row strings. Unknown operational receipt metadata profiles or historical source package binary versions reject; supported receipt metadata is not an exemption from the inner package checks.
- evidence-intake: metadata exactly `{custodySeq,evidenceId,requestDigest,binding,sourceSha256,relativePath}`. custodySeq actual positive integer locating the original Register line; requestDigest equals history key and original source path digest; evidenceId matches original custody/evidence row. binding equals the parsed original PREFIX payload binding exactly. sourceSha256 and relativePath equal evidence metadata and original bytes. createdUtc/updatedUtc/sourceArtifactSha256 all null. Imported inactive digest index uses these validated values, never a new generated digest.

URI validation is decode-and-compare, never fetching. href starts exactly '#/', no scheme/authority/backslash/control characters/extra fragment; query uses strict percent-decoded UTF8 key/value pairs with no duplicate keys. Allowed keys must occur exactly (order arbitrary); decoded case must equal package caseId. Preserve original href bytes, do not canonicalize it. Rules:
- evidence: path evidence, query {id,case}; id equals citation.id; sourceRef exactly evidence/<id>.
- interview-crosscheck: path interview, query {case,id,statement}; id resolves included recordId, statement equals citation.id and resolves that record's crossCheck; sourceRef exactly interviews/<recordId>/crosscheck/<statementId>.
- recommendation: path recs, query {case,id}; sourceRef recommendations/<id>; registered forbidden.
- colreg-check: path colreg, query {case,check,run}; check equals citation.id; run nonempty; sourceRef colreg/current/checks/<id>; registered forbidden.
- whatif: registered forbidden. Explicit missing placeholder path analysis query {case}, id/sourceRef W14. Existing unresolved scenario form path analysis query {case,scenario}, scenario nonempty, sourceRef nonempty <=512; never resolves to restored scenario.
- systemic: registered forbidden. Explicit missing placeholder path systemic query {case}, id/sourceRef W15. Existing unresolved item form path systemic query {case,id}, id equals citation.id, sourceRef nonempty <=512; never resolves to restored entity.
- reportHref: path report query {case,report}; values equal doc identities.

Registration flags exact: registered=>unregistered:false; unregistered=>true; missing=>false. missing/unregistered UI explicitly indicates unresolved and must not auto-navigate as restored source. The known optional needsReview boolean is preserved, not recalculated into a historical finding. Unsupported historical URI variations cause whole refusal rather than rewriting links.

## 14. Snapshot operation shape whitelist

Every snapshot doc has exactly `{reportId,sectionId,sentenceId,reason,beforeValue,afterValue,summary,auditSeq}` with nullable IDs, reason/summary strings and positive integer auditSeq. UTC/operator/action come from the linked original audit line, not invented snapshot fields. reportId null requires sectionId/sentenceId null. Nonnull section/sentence identify an included report target, except historical replaced target resolved through the validated before/after snapshot rather than requiring a now-removed generated sentence. Unknown target history rejects if it cannot be resolved without inference.

Use existing report schema definitions R=full report, S=full section, T=full sentence. Review snapshot S-/T- means exact schema keys except top-level reviews omitted by the existing algorithm; nested sentences retain their schema fields. Add archive validators for this precise omission, not arbitrary dict acceptance. gisis D uses existing report.schema.json gisis definition; F uses its gisisField definition. Error E exactly `{fieldId,code,message}` strings. Allowed known error codes are field_unknown, field_required, field_type, field_enum, field_range, field_length, field_pattern, field_checksum, field_utc; values dictionary is finite JSON keyed by field IDs, retains originally unknown field names when paired with field_unknown errors. No arbitrary additional snapshot keys.

| original audit action | reportId / targets | beforeValue | afterValue |
|---|---|---|---|
| report.generate | present; no targets | null | R matching reportId, family root/version |
| report.colreg.draft | present; no targets | null | R; still rejects any registered unsupported COLREG citation |
| report.regenerate | present; no targets | parent R matching parentReportId/family | new R matching reportId |
| report.review.confirm | present; section required; sentence optional | S- or T- | same target shape; historical status Confirmed |
| report.review.dismiss | same | S- or T- | same target shape; historical status Dismissed |
| report.review.modify | same | S- or T- | same target shape; historical status Modified |
| report.export | present; no targets | exactly {status: report status enum} | exactly {format:pdf\|docx,lang:zh\|en\|bilingual,sha256:lowercase64hex} |
| report.gisis.validate | null/no targets | D same caseId | exactly {values:object,valid:boolean,errors:E[],fields:F[]} |
| report.gisis.export | null/no targets | null | exactly {format:json\|csv,validated:boolean,sha256:lowercase64hex} |
| report.gisis.export_rejected | null/no targets | null | exactly {format:json\|csv,validated:false,errors:E[]} |

No report-rendered PDF/DOCX bytes are silently promised by the report.export digest: the old exporter streams these and does not persist them. Stored report history preserves the hash and operation, not a fabricated original rendition. Any separately existing per-case export file must pass artifact allowlist/budget handling or cause refusal, not be omitted.

Audit mapping validates category Report, entity_type report/gisis and entity_id reportId/caseId; raw snapshot_ref equals row key; reason agrees exactly. Review entries embedded in current docs map action confirm/dismiss/modify to the corresponding full audit action and before/after values. Audit summaries are intentionally truncated, so do not equate their before/after strings to full values. All global report events requiring a snapshot need one; do not require reverse bijection for unrelated non-report events. New import/export system audit appends after restored original sequence only. The chain authenticates internal linkage, not original reviewer identity or substantive findings.

## 15. Supported historical package checks and provenance limits

Historical source packages remain byte-preserved history, never executable authorization, policy or trusted identity. V1 export AND fresh import reject the whole outer archive if any referenced historical packageVersion is not exactly1.0.0,1.1.0 or1.2.0. No external registry/signature mechanism is introduced and no unknown-version cross-database recovery is promised.

For every unique historical source artifact, perform bounded in-memory read-only ZIP inspection without extracting files to disk: validate safe member names, collisions, encryption/CRC/size limits and strict manifest JSON; validate MCIS-MCASE format, supported packageVersion, complete manifest membership, declared sizes and SHA256 against every actual member; read case.json and case.ext.json under their existing strict basic schemas and check caseId agrees with inner manifest, outer caseId and importHistory association. Do not call import_case, invoke domain validators/LLMs, follow hyperlinks, apply its access-policy or activate any receipt. Its working-record/HFACS business payload is only hash-checked bytes in this historical inspection, NOT executed or certified as recoverable business state.

Inspect each unique indexed artifact once by SHA; no recursive discovery or execution of nested archive members. Such embedded member bytes still count in this artifact's expanded-byte/hash checks. All actual inspection decompression shares ONE bounded budget across the outer package and every inspected historical source: sum of outer expanded member bytes PLUS expanded bytes consumed from every unique inspected historical artifact <=64MiB, total visited ZIP members<=2048; each inspected member<=16MiB, each ZIP input<=32MiB. Stop streaming as soon as a budget would be exceeded; count streamed bytes as well as declared lengths. An artifact already present in the outer archive consumes its outer bytes AND its inspection expansion. No fresh64MiB budget per artifact or level. This deliberately rejects some otherwise size-valid old archives; errors explain aggregate history-inspection budget exhaustion. Compressed outer deliverable still<=32MiB; one historical artifact file still<=16MiB. Export preflight uses exactly the same counters/rules as import.

Every historical artifact is referenced in the explicit external lineage index; only those indexed objects are inspected, never a recursive ZIP traversal. External DAG depth8 describes declared protocol lineage, not proof of the opaque binaries' actual embedded depth. Matching manifest/case/hash verifies structural association and transport consistency, NOT authenticity of the source, reviewer identity, permission ownership or data legality. Imported JSON and SHA alone cannot authenticate any of those claims. UI labels history unverified/self-reported; the outer default policy is destination access control, not permission imported from an inner package or a compliance certificate.

Export also verifies the service's existing local source.mcase path, active intake row(caseId/digest/byteLength), current case and stored bytes agree before representing that active source as history. Previously imported archived metadata remains unverified history, never promoted by repeated export. Missing/conflicting local association or inner manifest/case relation rejects, without inventing records or accepting a request-body assertion as a local intake receipt.

Three-database acceptance uses supported known-version packages and checks structural association plus exact retained bytes under the unified budget; it does not claim cryptographic provenance authentication. Unknown inner versions and budget overflow explicitly fail with unchanged data.

Review time precision clarification: review_section obtains its UTC before append_operation/audit obtains a separate UTC. Preserve both original valid UTC strings; they may cross a second boundary. Never require equality or invent a maximum time-difference threshold. Link by validated auditSeq/action/actor/reason/target/values, not timestamp coincidence.


## 1.4.0 candidate amendment (2026-11-14)

For the bounded working-v1 plus timeline combination only, see [report-timeline-archive-v1.md](report-timeline-archive-v1.md) and timeline-records-archive schema. That versioned contract supersedes this document’s timeline_events refusal and historical-version enumeration for1.4.0. Unknown states and all other guarantees remain unchanged; old versions retain their original meaning.

## Standalone consultation export preflight

A case containing consultation_rounds must enter the existing history-aware export
preflight even if it has no reports, interviews or timeline. Consultation remains
unsupported: after existing full-content authorization, export returns409
ARCHIVE_RESTORE_UNSUPPORTED without a partial ZIP or export audit write. Default
unauthorized roles retain403. This does not introduce consultation restoration,
accept legacy nonempty consultation packages, or change1.0–1.4 parsing.
