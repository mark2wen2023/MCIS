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
