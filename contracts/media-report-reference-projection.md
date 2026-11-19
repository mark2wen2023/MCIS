# Internal saved-media report projection / 1 (not wired)

Base: candidate/media-demo-launcher at 76d6c22c474172a28f7b2da9ae45021e8d573b82.
Implementation: service/mcis_service/reports/media_reference.py.
This is an internal candidate contract, NOT an HTTP/report.schema extension,
a persistence format, an authorization receipt or a report-ready declaration.

## Trusted input boundary

Only a future trusted server adapter may invoke project_saved_media after existing
case/source authorization. It must copy persisted ORM row attributes into
`{case_id, run_id, revision, doc}` and supply evidence service `derive/list_items`
results from an appropriately consistent read. Do not use client-supplied row
identity, docs, source hashes, role assertions or an HTTP result relabeled as a
trusted row. The function cannot prove provenance of dictionaries; no endpoint
or application call site is added in this candidate. Authorization intersection,
source bytes/task verification and same-read semantics remain integration gates.

The selection `media, case_id, run_id, revision, evidence_id, evidence_role` selects
already saved rows; it cannot create identity. Media is audio or image. Revision
is an integer 1..1000, per the existing app.py human-revision limits; booleans,
zero, null and latest are invalid. Revision zero is the immutable initial record,
not a human revision. Each supplied row must have the selected case/run identity,
revision numbers must be unique, initial and exact human row must exist, and
human doc revision/expectedRevision must agree with the saved row. No requirement
to provide all intermediate history: this projects an exact row, not verifies
the entire audit/revision chain. Later revisions may be supplied but never chosen
as fallback. No client text is accepted separately from the saved human doc.

## Fields grounded in existing storage

- Audio `audio_review/app.py`: initial.machineDraft.source contains caseId,
  evidenceId, currentSha256, registeredSha256, stateDigest. The source current
  SHA is the byte version the draft binds; registered SHA and stateDigest have
  distinct semantics and are retained separately, not substituted for it.
  Human revision audioSha256 and machineArtifactSha256 must match initial
  source.currentSha256 and machineDraft.artifactSha256. draftBytesSha256 is the
  saved JSON artifact byte digest, not the semantic machine artifact digest.
  segmentId must select exactly one `id` in transcript.segments/unlocatedSegments.
  Hearing status is retained; unintelligible text must be empty. No timestamp or
  speaker claim is generated; future presentation must handle those separately.
- Image `image_review/app.py` and `tasks.py`: initial.sourceVersions has separate
  PDF, image, raw, candidate entries. Both PDF/image evidence IDs and SHA-256
  must exist. Their hashes must match candidate.source.pdf_sha256/image_sha256.
  Raw hash must match candidate.source.raw_sha256. Raw/candidate byte hashes are
  retained without inventing evidence IDs: local-task artifacts legitimately
  lack them. lineIndex selects a saved candidate text_lines entry. The human
  decision is not original-authenticity or PDF-page verification.
- Evidence inputs use caseId, evidenceId, **currentSha256**, matching the existing
  derived evidence view. Bare registration sha256 is not a substitute. Each
  required media source must resolve exactly once in the supplied items and
  match its saved digest. Same-ID other-case entries block, not auto-pair.

Evidence role is explicit: audio, pdf or image. No order-based pairing or source
selection is performed. Image requires both original-source roles even when the
chosen citation role is only one. SHA-256 is strictly lowercase 64-digit hex;
unknown/illegal hashes are not normalized into a match. Identifiers compare
exactly without trimming/case folding. Extra unrelated evidence items are not
interpreted as media sources. Full machine contract validation and task binding
are prerequisites of the future adapter, not duplicated here.

## Output and unavailable results

Success produces a detached projection fixing caseId, evidenceId/evidenceRole,
media, runId, revision, segment/line target, all original-source role digests,
artifact digests and the saved human text/review state. Flags factVerified and
associationPersisted are false; validationScope explicitly limits the result to
saved declarations and observed register. It is not the existing public citation
object and supplies no href. reports/sources.py remains unchanged.

ProjectionUnavailable.code distinguishes invalid_revision, no_human_revision,
initial_missing, revision_missing/mismatch/ambiguous_revision, case/run/evidence
mismatch, source_changed, source_digest_unknown, saved_source_mismatch,
evidence_missing_or_ambiguous, target_missing_or_ambiguous, invalid_identity,
unsupported_media_role and saved_shape_unknown. No partial citation on failure.
No read, write, retry, latest fallback or mutation of supplied rows occurs.

This check sees current supplied declarations only: equal hashes cannot establish
no A→B→A history or current file bytes. Source changes block a new projection;
no existing report is rewritten. A future fixed historical resolver must retain
old reference data and report current-source differences without substituting
latest. Export/reopen, archived media restoration, audit binding and historical
source availability remain unimplemented. Do not expose this projection until
those contracts and permissions are reviewed.
