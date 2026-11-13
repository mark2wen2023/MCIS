# ET-0 Evidence comparison timeline: isolated contract and model

Status: proposal/prototype only, 2026-11-13. No production routes or UI modified. No OCR, ASR, video understanding or real LLM connected.

## Existing integration points inspected
- W2 `MultiTrackTimeline` aggregates numeric simulation-time tracks. Keep it for its existing calculation semantics; do not silently coerce uncertain human evidence into precise simulation samples.
- W10 `TrackPage` reads saved points relative to case UTC epoch, has identity/navigation clearing and separate first UTC CSV input. Reuse its case selection and provenance links, not its point-only precision assumptions.
- PR44 investigation issue-card design supports versioned source references, low burden viewing and optional issue creation. Timeline browsing must not create cards automatically.
Inspection was of local `pr34-integration/tree` and `investigation-workflow-design-0900` copies; no fresh whole-tree remote verification performed.

## Smallest product slice ET-1 (not implemented)
A read-only comparison view accepts saved AIS point references plus manually recorded evidence events. Three parallel lanes initially: track data, interview excerpts, manual photo/video markers. Operators may view or compare without submitting reliability forms.
A manual marker requires source/version/locator and original wording, then either an explicit time, a user-entered range, or relative before/after references. Never invent a tolerance such as +/-30 seconds for 'about three minutes'; preserve original wording and ask an optional uncertainty entry, otherwise retain unresolved semantics.
Every lane shows observed text/time, origin clock/timezone, available calibration status and whether extraction is manual or AI candidate. Clicking a marker resolves a typed authorized locator, not arbitrary external URLs. Hidden or superseded sources display unavailable/stale without leaking original content.

## Model and calibration contract
- SourceRef: caseId, entityId, revision, digest under existing entity rules, typed locator. Source bytes are never modified by timeline display.
- EventRevision: immutable id/revision, sourceRef, original wording, clockId, kind(point/range/relative), precision statement, creator, recordedAt. An exact point denotes recorded precision, not guaranteed physical truth.
- Absolute adapter must require explicit UTC offset/zone semantics and preserve original timezone; unknown timezone/ambiguous local time cannot be guessed. Convert to the common case epoch only after explicit basis. Prototype starts after this adapter and takes decimal relative seconds.
- CalibrationRevision: case, clock, scope (selected source/version and raw time span), offset sign defined as displayed=raw+offset, uncertainty, method/basis refs, proposed/confirmed/rejected, actor and previous revision. Constant offsets cannot represent drift or discontinuous clocks; split scopes or retain unresolved, never extrapolate globally.
- Confirmed zero offset is explicit alignment evidence, not a default. Proposed offsets never automatically affect authoritative view. Changing calibration creates another version, not mutation; comparison uses one explicit selection per source scope, with old views reproducible.
- Range display expands by calibration uncertainty. Disjoint calibrated intervals permit a temporal ordering only; overlap does not imply same event or conflict. Unknown alignment means no cross-source temporal conclusion. Relative-only events have no invented numeric timestamp. Relation cycles are flagged for investigation, not resolved by deleting evidence.
- Event matching and conflict finding remain human/AI proposals. Same timestamps do not prove identity, and different timestamps do not prove contradiction.

## Product consistency and integration gates
Manual writes will require trusted server actor, case authorization, revision check, idempotent request, atomic persistence and no-store. No new writes until archive policy is explicit: complete source/calibration/event history must be exported or export must explicitly reject unsupported data, never omit it. This prototype has no API, database, auth, receipt or archive behavior.
Selected discrepancies may create a proposed issue-card payload retaining source refs and selected calibration versions; user must confirm creation. New source/calibration versions mark dependent views/questions as needing review, never rewrite old judgments or discussion packets.

## Prototype scope
`timeline.py` is a pure standard-library immutable value model. It checks basic point/range shape, provenance presence, finite bounded decimal seconds, correction case/clock/basis, uncertainty-expanded intervals, uncalibrated conservative comparisons, and relative graph cycles. It does NOT implement scoped calibration spans, timezone conversion, drift, strict serialized input parser, source permissions/digests, trusted confirmation, graph-vs-absolute contradiction detection, revision store, full field validation or production resource protection. Strings/status are trusted fixture inputs; frozen dataclasses are not security isolation.
18 unittest cases pass locally. No C#/.NET/NuGet/browser execution, no dependencies installed, no real source extraction. UI and cross-module behavior remain untested. Independent review is required before claiming integration readiness.

## Decimal precision correction after independent review
Independent review found that unrestricted fractional digits could be rounded by Python's default 28-digit Decimal arithmetic even when applying a zero correction. Distinct raw times could therefore collapse. The prototype now accepts ONLY fixed-point seconds with at most 9 fractional digits and absolute input value <= 1,000,000,000,000 seconds, without exponent notation, whitespace, plus signs or non-ASCII digits. Overprecision is rejected rather than rounded. This representation does not assert that evidence is accurate to nanoseconds. Original source wording remains separate and unchanged; adapters must not truncate unsupported source precision silently.
Arithmetic uses a private precision-32 Decimal context. The three bounded operands have at most 22 significant digits in the resulting sum/difference, so these operations are exact within the supported contract regardless of caller precision. Correction-expanded bounds may reach +/-3e12 seconds; the 1e12 bound applies to individual inputs, not the calculated view.
Six regression tests were added: excess precision rejection, one-nanosecond distinction at a large magnitude, independence of a precision-3 caller with rounding traps, fixed-point grammar, correction precision limits, and input/expanded bounds. Current local result: 24 unittest tests passed; this revision was subsequently independently rerun by the review worker: 24 tests passed, per parent confirmation. No production integration acceptance is implied.
Remaining gap explicitly retained: cycle detection concerns only the relative-order graph. A recorded 'A before B' relation that contradicts calibrated absolute intervals is NOT currently detected. The prototype must not be treated as a globally consistent event ordering or an automatic discrepancy detector. No production code, API or data changed.
