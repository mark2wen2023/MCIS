# Caller-supplied declaration comparison — isolated research, NOT application wiring

Base/design: 06a7e8b5eabd6e85b3d65c9be98a5938431ea3c5, docs/design/MEDIA-INTERVIEW-SOURCE-CONTRACT.md. No UI/backend imports or registration. compare.mjs has no imports and does not access network, filesystem, database, clock or random source. Pure functions return new results, do not create associations, audit, authorize reads or authenticate callers. Existing GET endpoints can have audit/byte-read effects; they are not called here.

## Input scope and revision basis

Inputs are caller-provided plain, acyclic JSON-like declarations (optional/missing properties supported); not arbitrary JS proxies/getters, cyclic objects or executable data. No API adapter is supplied. ComparePair accepts interview/media envelopes `{state:'available',data}` or unread/unavailable, explicit selection `{caseId,mediaKind,runId,reviewRevision,sourceRole}`, roleDeclaration and historyEvents. Unavailable payloads are not traversed/echoed. Data paths follow the design's fixed media baseline 76d6c22c474172a28f7b2da9ae45021e8d573b82. Do not feed lists as detail responses.

Review revision validation is **integer 0..1000** for this fixed candidate only: contracts/audio-review-candidate.md and contracts/image-ocr-review-candidate.md describe initial revision 0 / maximum 1000 human revisions; audio_review/app.py initial insertion is revision=0 (line121), append cap/increment lines155–157; image_review/app.py initial line84, cap/increment lines129–131. This is a pinned candidate output range, NOT a new server API constraint or a guarantee for future/legacy arbitrary data. Boolean, string, negative/fractional/out-of-range and absent revisions cannot compare equal. Machine transcript revision is not used. Whole-interview stable revision is unavailable; an optional caller-supplied `version` is opaque snapshot material only, never certified as a server version. No persistent association is supported.

Roles: audio, pdf, image (page image), image_raw_output, image_candidate. No default role. RoleDeclaration requires role, nonblank basisText, declaredAt and declarerProvenance plus boundSnapshot from declarationSnapshot(interview data). Timestamp/provenance are opaque assertions, not clock/identity verification. The snapshot binds identity, evidence ID, source hash and optional version, retaining presence/null semantics. An empty historyEvents array means only “caller reported no intervening change”, NOT complete history. observeDeclaration consumes explicit snapshot_observed events; any differing snapshot invalidates permanently through A→B→A. Invalid/missing event history is unknown. No event collection, persistence, trusted sequence, server history or React observation guarantee exists.

Audio uses currentSha256, not registeredSha256/stateDigest. PDF/page-image/raw require both specified hashes; candidate uses its independent sourceVersions hash. Each missing/null/empty/invalid/present field is separate. Valid digest comparison lowercases hex, never trims; IDs remain exact and evidence comparison uses only EV-digits subset, not all server ID validity. Internal mismatches and ID/digest differences are independent issues; mismatches do not mean tampering. Across cases source payload comparison is skipped; case/identity input fields still reported. Unsupported audio machine output role is invalid/indeterminate.

compareDeclarations accepts `{requiredRoles, pairs}`. Each pair explicitly identifies a candidate; no array-position/hash/name pairing. Duplicate roles are ambiguous even for equal claims or different runs/revisions. Missing/unexpected required roles block overall equality. Mixed cases block overall equality. Each pair result remains visible; one equal pair never hides another failure. Consumers must interpret `declarations_equal` only as caller-supplied declaration equality, not current bytes, authenticity, reading/listening, approval or interview linkage. Outputs always have association=not_established and verification=not_performed. This is not an untrusted-input security parser.

## Development validation only

After static safety review, ran only:

```sh
node research/source-declarations/compare.test.mjs
```

13 synthetic groups passed: five roles; digest case/ID distinction; independent missing/null/empty/invalid states; multiple errors; dual-image hashes; audio hash non-substitution and task artifact missing ID; revision bounds/selection; role missing/mismatch; explicit history ABA/unknown; unavailable payload non-access; duplicate/required roles and reordered explicit pairs; deep-frozen input unchanged; stale snapshot, wrong selected run and mixed-case group. Test data is handmade, no stored case/media or backend imports. Global fetch throws. Node's normal source-module loading is the only file reading required to run the test; comparator itself has no I/O. Earlier 12-group pass preceded an added explicit stale/selection/mixed-case group; do not sum counts.

No browser, HTTP, application startup, model, byte verification, permission/refusal, paused, archive or recovery tests ran. No new dependencies. No service aggregation, audit/association writes, automatic role inference or persisted authorization. This candidate awaits independent review; not production-ready, no merge/deployment. Repository checkout is not sanitized data. No original materials are included in this increment.

## Aggregate identity correction (after e6bed46)

The aggregate represents one interview and its explicit role declarations, not a batch of independent interviews. All readable pairs must share exact caseId/recordId and the complete declarationSnapshot: caseId, recordId, record.evidenceId, record.sourceSha256, optional opaque version. This is not the whole interview body or a trusted server revision. Snapshot equality is structural (key order irrelevant), retains missing versus null, and conservatively retains raw hash spelling. Pair-level hexadecimal digest comparison remains case-insensitive. No snapshot field is selected from another pair or normalized away.

The aggregate now separately reports case_mismatch, interview_record_mismatch and interview_snapshot_mismatch as applicable, returns indeterminate and retains individual pair results. Invalid/missing identity remains a pair error that also blocks aggregate equality. Pairs failing the existing read-state gate are not traversed for snapshots. No role inference, association or service access was added.

Static-reviewed new aggregate.test.mjs uses handmade plain fixtures, controlled unavailable-payload getter and node:assert only; fetch throws. Before correction, its first assertion reproduced two individually equal different interviews incorrectly producing overall declarations_equal. After correction, only these commands ran:

```sh
node research/source-declarations/aggregate.test.mjs
node research/source-declarations/compare.test.mjs
```

7 new aggregate groups passed; the existing 13 groups passed separately. Do not add these into full-system coverage. New cases cover different interviews, source ID/hash/version differences, missing/null, property order and role order, unavailable payload non-access, explicit caller ABA, and cross-case differences. These are development tests awaiting independent review; e6bed46's earlier 13 groups were independently confirmed, not this fix. No app, backend, browser, media, database, clock, model or case data was used. Node loads only the test/module source; the comparator has no I/O. No paused/refusal/write-probe tests ran. No claims of server history, original authenticity or production readiness.
