# Read-only supplied audio bytes and declared v3 result consistency

Base: ef53c32c6f1c848739d34b715c685a4a70bde8d8. Branch: research/media-byte-consistency.

## Implemented bounded profile

`byte_consistency.check_audio_members(index, payloads)` first applies the existing offline member/association validator, then accepts **audio sources only**. It receives in-memory bytes; it cannot open paths, read product originals, query a database, execute a model, download dependencies or write any output. All success flags still deny restore/export/authorization/execution/authenticity approval.

For supplied original WAV bytes: SHA256 must match member metadata and both registered/current declarations; RIFF/WAVE envelope length must match the complete supplied bytes. Existing PCM subset is checked via Python wave: uncompressed,1–60seconds,8–48kHz,1/2channels,1–4byte samples. Decoded frame count, rate, channels and width must exactly match the declared sampling clock, including fractional-millisecond duration. No rounding of the actual endpoint, truncation, resampling or zero filling. This bounded RIFF profile may reject other legitimate WAV variants and does not add support for them.

Rebuild the *declared* source snapshot using case/evidence/receipt ID, matching digests and actual frame clock; match it to the saved machine draft. Receipt ID/state digest is only consistency of supplied declarations, not a trusted server receipt or proof of authorization. Reuse the existing native `sample_machine_contract.validate` for full v3 machine field/digest validation. Earlier machine revisions lacking parent history are rejected.

Retained raw recognizer JSON must equal the machine's recognizerResult; its canonical JSON digest must match the native field. Model revision/weight digest/runtime versions/parameters metadata must agree with that raw result. Re-run the **offline converter**, not ASR, and require the entire native v3 draft to equal its deterministic result for the retained input. Human revision segment IDs, audio/machine digests, text/hearing declarations are checked; the existing outer validator checks exact time bounds and unknown speaker/time. This is not a conclusion that any recognized words or human statement are correct.

The inherited outer index currently expects raw-member SHA to equal the native canonical result digest. Accordingly this bounded slice uses the task's original canonical JSON serialization; external differently formatted JSON is not silently normalized/rehashed to qualify. Broader raw-file transport versus canonical-document digest compatibility remains a separate prerequisite.

## Ordinary developer tests

Command (repository root):
```
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q research/media_archive/test_contract.py research/media_archive/test_byte_consistency.py service/tests/test_media_archive_preflight_research.py --tb=short
```
Result: **83 passed in4.91s**, no failures/skips. Distinct selection:42 existing member-contract tests +26 new byte-consistency tests +15 native-inventory tests. Earlier20 and57 results overlap and must not be added. Developer-only result; no independent acceptance yet.

New fixtures generate actual PCM WAV bytes (silence) in memory with16000,16001 and88747 frames, but recognizer text/results are explicitly fabricated. Existing converter-required scope strings do NOT mean a model ran. Test missing members, inconsistent sample declarations, malformed RIFF, v2 refusal, missing segment association, native-valid draft differing from declared converter output, and raw out-of-bound timestamps retained as alignment_pending with no located segments. No speech recognition, real case, real original-file access or browser verification occurred.

## Remaining blockers

- Image/PDF byte/header/page/render validation is not implemented; that profile explicitly rejects. No page count or image-to-PDF lineage is inferred.
- No assembly from the native database inventory, consistency across file/DB snapshots, source-access permission check, publication or restore. Input provenance remains caller-supplied; hashes are not authentication.
- Audio v2 without preserved raw result remains unsupported. No old result/history is fabricated or rewritten.
- Invalid/unpaired model timestamp arrays remain raw untrusted output; successful consistency does not make them usable timing. Emotion/speaker/authenticity/recognition execution remain unverified.
- Product archive protection and all permissions remain unchanged. No protected/restricted security/ECFC/browser suite, model/API, PR-body operation, merge or deployment.
