# Audio review isolated candidate, version 1

This opt-in application is separate from the default product app and from the image candidate. It imports existing `MCIS-AUDIO-MACHINE-DRAFT-2` revision-1 JSON; it does not execute ASR, manufacture recognition results or approve a transcript. Human corrections never replace the original registered audio or machine artifact.

## Admission and source binding

Use existing evidence intake preview/commit to register audio and draft JSON, retaining both originals. Explicit factory `mcis_service.audio_review.app.create_audio_review_app(settings)` creates the separate append-only `audio_review_revisions` table and mounts `/audio-review-lab`. Default `create_app` does neither. Run only on 127.0.0.1 in a disposable candidate store; repository root and service must be on PYTHONPATH for the existing offline contract validator. No installation or automatic launch is supplied.

All candidate record operations call the existing evidence-intake authorization function (write mode for changes). Downloads use the existing authorized intake download endpoint; no new unrestricted file route. This retains existing policy and self-reported role-header limitations; it is not SSO or an independent security review.

`GET /api/v1/cases/{case}/audio-reviews/source/{receipt}` reads the registered bytes and accepts complete uncompressed PCM WAV only: 1–60 seconds, integral millisecond duration, 8–48 kHz, one/two channels, 1–4 bytes/sample. SHA256 must match the receipt source/current digests. State digest binds case, evidence ID, receipt and those digests. This byte association is not authenticity verification, proof of listening or proof of ASR execution. `trackIndex=0` identifies the whole WAV stream, not a person or individual channel. Durations outside the slice fail rather than truncate/round.

`POST .../audio-reviews` requires exactly audioReceipt, draftReceipt, acknowledgeArchiveBlocked=true. Validate UTF-8 machine JSON (262144-byte limit, no duplicate keys/nonfinite numbers), unchanged v2 hashes and exact source snapshot. Missing parent machine history (revision >1) fails; no invented parent. Maximum 20 runs/case. The initial revision 0 retains the complete machine artifact, raw JSON digest, format, author declaration and existing audit entry. Model/provider fields are imported claims; the inspection still says executionVerified=false. Repeated attachment is not idempotent: after an uncertain result, inspect saved runs rather than automatically retry.

## Revisions and replay

`GET .../audio-reviews` lists run IDs/times only; it does not check source bytes. `GET .../audio-reviews/{run}` rechecks both registered originals before exposing the original plus all revisions. A stale/unavailable original fails; no rebinding. Revisions and audit append in one SQLite transaction, using existing write-lock handling. SQLite update/delete triggers reject mutation of stored revisions. This is not a signature or protection against an operator who controls the database.

`POST .../{run}/revisions` accepts exactly expectedRevision, segmentId, text, hearingStatus, startMs, endMs, reason. CAS mismatch returns 412. Text/status/time changes append a full segment revision linked to the original machine artifact/audio digest; previous revisions remain. Maximum 1000 revisions/run. hearingStatus is pending, transcription_checked (an operator declaration, not fact approval), or unintelligible (requires empty text). Times are either both null (unknown), or integer milliseconds `0 <= start < end <= duration`. No inferred time, speaker identity or zero replacement. A reason is required. Empty text alone is not proof of unintelligibility. Original unlocated segment reason remains in the original artifact even if a later operator supplies a range.

Page explicitly fetches the authorized original, checks downloaded SHA256 against the saved version and response header, then creates an in-memory audio Blob. No automatic play. Segment buttons use current operator-entered range, visibly labelled if unsaved. Unknown time permits whole-file listening only. HTML media timeupdate stop is approximate, not sample-accurate. Browser decoding/playback is untested; format acceptance does not promise every browser decodes every PCM width.

Failures preserve input and never auto-retry. Success must match the run, revision, immutable initial artifact, preceding history and submitted segment fields. Drafts remain page-memory only; refresh warnings can be suppressed by browsers. No identity-change guard or durable draft recovery is claimed. Clearing/case changes/pagehide revoke the Blob. Responses use no-store; no localStorage/external scripts.

## Compatibility and limits

No product permissions, current archive whitelist, default routes, shared EvidencePage or existing schemas are changed. Nonempty candidate records cause existing whole-case archive protection to return 409: archival/restore is NOT supported. Users explicitly acknowledge this before attachment. No existing old transcript migration, external ASR/provider, real speech sample, diarization, browser verification, true crash test, production identity or production rollout. Ordinary tests use generated tone bytes and explicitly fabricated contract fixtures. No private samples, media binaries, model weights or databases are deliverables.
