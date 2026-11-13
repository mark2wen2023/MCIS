# SK-T01 source-bound preview adapter (research only)

Implements the first narrow adapter stage of draft PR #55. It does **not** implement the entire timeline Skill. This is an isolated, importable Python protocol prototype, not a registered API, installed Pi Skill, or user-facing feature.

## Existing mechanism reused

Request and response vocabulary derives from `tools/mcis-core/src/AlignCommand.cs` and `Program.cs` at main `3aba2bf03e393909c611489ae573a887087637ac`. All timeline computation is delegated to `core.align`; none is reimplemented here. Currently only NMEA inline text and uncalibrated comparison are admitted. `calibrate=False`, `emitGnssAnchors=False`; no default dates, paths, calibration estimates or manual anchors are accepted from the request. W2 diagnostics are not yet adapted. Zero candidates is explicitly **not** consistency or coverage proof.

## Trust and integration boundary

`principal`, `repository`, and `core` must be provided by a trusted host, never decoded from caller JSON. The repository must perform case/source authorization on resolve and atomically reauthorize/check revisions+digests on recheck. No permissive production implementation exists. Local Python object types are not security isolation; the tests' repository and principal are synthetic, not credentials or proof of authorization. Digests compare exact UTF-8 text snapshots, not original evidence file bytes; original binary/OCR extraction provenance still needs a real host adapter.

The core port must execute the existing W2 engine with timeout/output limits, a trusted executable and sanitized environment. This change intentionally does not ship an unsafe subprocess runner or claim that a fake backend executes W2. This environment has no dotnet; a real W2 roundtrip is **pending**. Upstream entries expose only unverified counts: per-conflict source linkage/diagnostics need a reviewed adapter. Epoch has an explicit offset; source NMEA timestamp semantics and device clock uncertainty are **not validated** by this prototype.

## Run local synthetic tests

```
cd research/skills_timeline
python -m unittest -v
```

19 tests (plus parameterized subcases), no third-party dependencies. `FakeCore` explicitly means simulated protocol responses, not an LLM or W2 execution. Tests cover malformed input, case/source mismatch, source content tampering, permission denial/revocation hook, revisions, budget, core failure, unsupported formats and zero-candidate caveat. Independent review results are recorded separately.

## Remaining acceptance gates

- Trusted real repository identity, authorization, snapshot locking and expiry handling.
- Bounded real mcis-core transport, actual W2 tests, full diagnostic adapter and source-level conflict references.
- Full uncertainty/timezone/clock-calibration policy from #55, cancellation/timeout lifecycle.
- UI, persistence/review, actual model explanations, model citation checks, report/archive integration.

No writes, network calls, model calls, external side effects, merge or deployment are performed by preview(). Output remains `needs_human_review`; it never confirms facts, event identity or responsibility. Do not merge or market this as a completed production Skill.

## 0.2 exact source-reference binding (2026-11-13)

Adds per-entry `candidates`: conflictId, human-review status and a/b references
copied from the selected Source snapshots. Based on conflict.schema.json and
ConflictJsonWriter at main 3aba2bf, sourceLabel is matched **exactly** to a selected
source ID. No aliases, fuzzy labels, same-source pairs, duplicate conflict IDs,
or upstream evidenceId claims are accepted. Unknown upstream text and values are
not forwarded. Unknown source mapping fails the entire preview before release;
final repository reauthorization/version recheck is still mandatory.

This only checks referential linkage to input UTF-8 snapshots. It does **not**
verify that W2 calculated a conflict correctly, that observation values occur in
source records, or that original media authenticates the text. Actual .NET/W2
runtime compatibility, line-level citations, full diagnostic forwarding and the
existing clock/uncertainty limitations remain unverified. `notChecked` now names
`observation_values_and_original_media`; no claim of full provenance completion.
Old README/REVIEW counts above document 0.1. Current test command runs 32 synthetic
unit tests; no real W2 or LLM is executed. Source metadata is now bounded text,
not arbitrary objects. New output still must be rendered as escaped text by a UI.

## 0.3 pre-compute recheck (2026-11-13)

Before passing source text to core.align, the adapter now calls the trusted
repository recheck for the entire resolved snapshot set. A false/non-boolean or
exception outcome stops before core invocation. The existing post-compute check
remains; no result is released if evidence/permission changed during computation.
This closes a missing check after sequential source loading, not all concurrency
races: the host still needs an atomic lease/transaction or equivalent policy
for the interval between recheck and dispatch. This code is NOT production
authorization. No real W2, database, media or LLM has been exercised.

Full test discovery currently includes 40 previous synthetic tests plus 7 new
preflight tests. The test doubles prove adapter order/rejection, not actual
permission revocation propagation or a production data-access guarantee.


## v0.4 import-quality summary (2026-11-13)

`importQuality` now distinguishes missing statistics (`unknown`), zero/partial
usable import (`insufficient_import`), and positive aggregate counters
(`coverage_unverified`). These states are not an investigation conclusion.
All counters remain explicitly core-reported and unverified. Positive totals
cannot show that both sources produced comparable observations, or that their
time ranges overlap. No state is named clean/passed/consistent.
Only bounded integer counters and a diagnostic count escape; raw diagnostic
messages are never forwarded into model/UI context. Source text, timestamps,
clock calibration, per-source coverage and time overlap remain unverified.

The field contract was read from `tools/mcis-core/src/AlignCommand.cs` at
`c945a20ebec713ead35d1c49d7fc1bf0c50ccaaa`, lines 179–199. This is a source
contract inspection, not an executed W2 integration test. Developer regression:
61 local synthetic tests passed (53 previous + 8 import-quality tests). This
checkout has no .NET runtime. No real W2, LLM, production permission store or
UI was exercised. This remains an isolated research adapter in draft PR56.
Executor: native subtask, not a Codex app task. No merge or deployment.

Independent reviewer added 6 tests; combined local synthetic suite: **67/67**.
Missing/null statistics deliberately remain unknown for compatibility; malformed
non-null supplied statistics reject the preview. Independent review approved
this limited draft scope, not production readiness.
