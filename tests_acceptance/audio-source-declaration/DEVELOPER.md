# Audio run source declaration — developer check

Base: d1f2593f98364bc54ee12ec02f8a3b1ccfdd0327 (candidate/media-demo-launcher).
Independent of PR99: no branch merge, link, automatic matching, selection or interview writes.

Contract review (static only): tools/audio_transcript_contract/contract.py source fields;
sample_machine_contract.py v3 retains the same evidence/digest fields;
audio_review/app.py source(), matched_source() and attach() retain the machineDraft source.
registeredSha256 and currentSha256 are separate declarations. The new display labels the latter
as current at the time of the run record, not today's verified original. Existing raw metadata
remains. Missing/invalid fields show unknown, never infer an evidence ID from a digest. Values
are assigned with textContent. Case/run input changes clear the new summary.

Safety review: only Node built-ins; sole file read is audio_review/review.html. Actual render()
runs against synthetic DOM and in-memory run objects; fetch throws and zero calls are asserted.
No application import, audio bytes, cases/seeds, model, browser, service or new dependency.
No paused/refusal tests selected.

Exact command from repository root:
```
node --test tests_acceptance/audio-source-declaration/page.test.cjs
```
First execution: 4 passed, 0 failed/skipped (developer synthetic tests, pending independent review).
Covers two accepted run states, missing/malformed source, distinct digests and literal text,
and case/run input invalidation. Direct render fixtures do not validate HTTP acceptance,
permissions or source truth. This does not verify browser layout, accessibility, listening,
original bytes, present registry state or matching with interview records. No full build/suite:
standalone HTML source, not the Vite frontend. No merge/deployment or archive enablement.
