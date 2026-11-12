# Working archive B API contract (PR36 implemented)

The two added GET routes are also declared in shared OpenAPI; this document specifies their detailed behavior. Existing package URLs and request shapes remain unchanged. Added successful preview/commit/recovery field:

```
workingRecordsExtension: null | {
  version: "MCIS-WORKING-RECORDS-1",
  interviewCount: integer >= 0,
  reportCount: integer >= 0,
  reportSnapshotCount: integer >= 0,
  manualReceiptCount: integer >= 0,
  receiptMode: "archive-only",
  identityMode: "unverified-self-reported"
}
```

packageVersion1.2.0 requires nonnull extension. Existing hfacsExtension remains independently null/present. Legacy saved intake receipts lacking this new field are not guessed to contain working records; parse their original package to determine supported summary. Counts are not permission to read content and not evidence of factual accuracy.

GET `/api/v1/cases/{case_id}/archive-history/evidence/{evidence_id}/content`: current full-content all12RO/RW/no applicable field rule, current case/evidence visibility, existing archived evidence-intake history required. Success200 attachment raw bytes with no-store after successful Access audit commit. This is not a receipt response. Ordinary evidence content for an archived-marked evidence ID returns409 ARCHIVE_HISTORY_ONLY after full authorization. All intake replay/recovery entry points for imported historical digests also return409 ARCHIVE_HISTORY_ONLY. The UI must not treat that as a completed current operation; an explicit history download can use the new route without inventing an active receipt. This slice adds no separate evidence-history metadata listing endpoint; existing evidence metadata remains original, and a403/404 must not cause a guessed history label.

Expected errors (existing errors also remain):403 FORBIDDEN with no state details;404 HISTORY_NOT_FOUND for no matching historical object after authorization;409 ARCHIVE_HISTORY_ONLY for inactive receipt/old content route;409 ARCHIVE_HISTORY_INTEGRITY for missing/corrupt historical source;422 WORKING_ARCHIVE_INVALID for unsupported or inconsistent archive;413 ARCHIVE_BUDGET for uniform count/byte/decompression budgets. All added routes and archive-related refusals no-store. No success response contains restored active credentials. Invalid/unsupported requests may retain existing package-specific422 codes; UI should show server code/message without guessing successful recovery.

Provenance GET is specified below; PR36 passed the recorded independent acceptance. Do not infer all current reports/interviews are restored just because their case has an archive extension.

## Reviewed provenance addition: latest restore only

GET `/api/v1/cases/{case_id}/archive-history/provenance/{kind}/{record_id}`, kind exactly interview|report. Response exact `{caseId,kind,recordId,provenance:null|{origin:'restored-history',sourceArchiveSha256,importedUtc,originalDocumentSha256,currentDocumentSha256,changedSinceImport:boolean}}`. The source is the latest active package-intake source, not a claim of earliest origin. No historical document receives extra fields.

All12 full-content gate precedes object lookup; current AND original archived sources must be currently visible. Same reserved transaction binds source package checksum, unique same-case/type record selection and current document comparison. No active intake =>null. Existing intake with missing/bad source bytes/manifest/case/schema/duplicate JSON/key =>409 ARCHIVE_HISTORY_INTEGRITY, never null. Only a completely validated original package with no working extension or no matching key returns null. Missing current object=>404 HISTORY_NOT_FOUND. Unauthorized=>403 without object existence detail; failure responses include no filesystem paths or metadata.

Document hashes use Python canonical JSON: sorted object keys, compact separators, UTF8, no nonfinite numbers, original array order/string content retained. It is an opaque server digest, not JCS. ChangedSinceImport compares those normalized document bytes, not original JSON whitespace, authenticity, signature validity or assurance that individual fields were professionally verified. UI labels “含恢复历史，后续操作另记” and explicitly distinguishes changed/current state. All responses no-store;403/404/409 must never generate an inferred history label. This read adds no history event and never replays a receipt.

History content success additionally requires `X-Sha256` equal to the server-verified original bytes; response<=16MiB, W4.1 evidence intake sources remain under their original8MiB limit. Client may verify bytes independently before downloading. Permission/hash/path/commit failure returns no success bytes or Access event.

## Legacy credential compatibility

This version rejects legacy archives containing evidence-intake custody credentials without the validated working-record extension, including attempted version downgrades or incomplete extension namespaces. It does not reactivate those credentials through either old import or restricted intake. This restriction applies to subsequent imports only: no automatic cleanup, migration or repair of credentials already active in existing databases is performed. Existing data is not rewritten.


## Track-history extension v2 (package 1.3.0)

See `track-history-v1.md`. Only a case containing supported W10 state selects package1.3.0/root working version2; summary version becomes `MCIS-WORKING-RECORDS-2` and adds required nonnegative integer `trackReceiptCount` (>=1 for1.3). All prior v1 summary fields remain and must bind through preview/commit/recovery. No-W101.0/1.1/1.2 remain unchanged. The single authoritative working member path remains backup.v1.json; do not infer envelope version from its historical filename.

Archived W10 inputs never return active `replayed` results. Their metadata and exact originals are separately authorized through `/archive-history/track-imports` endpoints declared in OpenAPI. Old data without either archived index or newly instrumented local-origin marker returns `TRACK_ORIGIN_UNVERIFIED`, not proof of failure or permission to resubmit. Original data is retained. Full restrictions, original-byte preservation and upgrade compatibility are specified in the versioned supplement.


### Existing restored-source provenance compatibility

The known legacy-W10 migration refusal remains HTTP422 `PACKAGE_INTAKE_INVALID` at package intake, with structured `detail.reason: TRACK_HISTORY_MIGRATION_UNSUPPORTED` only for that branch. When an already-restored database's original `source.mcase` hits precisely that refusal, the provenance GET returns HTTP409 `ARCHIVE_HISTORY_UNSUPPORTED`, not a claim that the original is corrupt. The original package and current report/interview remain unchanged; no migration, credential activation or file deletion occurs. Other parsing failures and source hash/receipt mismatches continue to return `ARCHIVE_HISTORY_INTEGRITY`. Current permissions still precede source inspection. `UNSUPPORTED` does not certify that all package contents are valid: the parser stopped at the known migration boundary; the provenance route has checked only its preceding stored-source byte/hash binding before that refusal.
