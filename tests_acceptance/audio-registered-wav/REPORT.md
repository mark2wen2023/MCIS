# Developer report — not independent acceptance

Basecdb15cbf4525f49e353428c469f126d8caa44f01; isolated branch candidate/audio-registered-wav. Existing default product app and permission policy unchanged. Optional runtime only; archived/import protections remain. No installer/downloader/network call added.

## Implementation
The former fixed public sample hash is replaced with actual authorized registration/source bytes. Narrow task scope:1–30seconds, mono16bit16000Hz PCM WAV,<=1MiB; no format conversion or altered original. Larger/different valid WAV may still use existing manual review, but task returns422 before task row/worker. Worker independently validates WAV bounds and the exact server-supplied SHA; result digest must agree. Only host-configured fixed local model and script; no HTTP file/model paths. Fixed languagezh; language accuracy beyond Mandarin not evaluated.

Original v3 frameCount/sampleRateHz rational duration remains authoritative. Reauthorization/source comparison at publication, duplicate-ID/unknown semantics, no retry/delete, preserved source/revisions and archive409 remain inherited. New registered-audio recognizer scope does not itself certify execution; converter still requires source digest and retains claims as pending.

## Ordinary selected tests
```sh
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q service/tests/test_audio_review_candidate.py service/tests/test_audio_sensevoice_candidate.py service/tests/test_audio_sensevoice_tasks.py --tb=short
node --test tests_acceptance/audio-review-candidate/page.test.cjs
```
32service pass;6syntheticDOM pass. Counts include inherited tests and must not be added to earlier totals. Tests use constructed PCM/stub recognizer; not real ASR accuracy or browser. Covers non-demo registration, unsupported sample rate/channels/width/31s/oversized byte payload refusal before dispatch, continued broader manual read, inherited lifecycle/unknown/rollback and pending revisions. No formerly restricted security/ECFC/browser test run.

## Actual model experiment with TWO inputs
```sh
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python tests_acceptance/audio-registered-wav/run_two_inputs.py /workspace/mcis-sensevoice-trial/sample/asr_example.wav /workspace/mcis-sensevoice-trial/venv/bin/python /workspace/mcis-sensevoice-trial/model /workspace/mcis-sensevoice-trial/registered-two-inputs
```
Real local fixed child process on each input, not mocked output. CPU4threads, FunASR1.2.6/torch2.6.0+cpu/torchaudio2.6.0+cpu/numpy1.26.4. Official model revision3847d57b6bdf2dd8875cb1508d2af43d80a16bf7 and weights833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea. Existing source/license/install manifests inherited; no downloads this turn.

1. Public FunASR ordinary Mandarin demonstration (same exact original source and upstream MIT/reference as prior report),88747frames/16000Hz. Model load5.764858s, inference0.559581s. Text matches upstream reference; this is not independent listening. Raw19timestamp pairs have no explicit words, final5550ms exceeds real5546.6875ms. All remain unlocated, unchanged raw output retained. Real task->draft->pending reference-based human edit->restart/download exact-original/archive409 passed.
2. Generated1-second all-zero PCM,16000frames/16000Hz, explicitly synthetic NON-SPEECH, not a real person. Actual model load6.649594s, inference0.231144s. It hallucinated 嗯 and returned0–990ms. Task status succeeded means the pipeline published an unreviewed output, NOT recognition correctness. False positive is retained and reported; no fabricated human approval or source text. Unlocated draft/speaker unknown retained despite in-bounds model timestamps. Original bytes unchanged, repeatID409, restart status succeeded. UI warns silence can yield erroneous words and requires human listening.

Actual trial output/worker logs kept locally under /workspace/mcis-sensevoice-trial/registered-two-inputs/{public-speech,synthetic-silence}. Binary sample/model/database/output are NOT included in commit. Script is opt-in, with existing local dependencies; no external inference. Final code-only difference after execution changes report boolean to workerResultPresent (more precise than asserting model execution for all possible future failures), not the exercised task implementation.

## Limits
Only developer tests; no independent review, real browser/audio playback, noisy/private/multilingual/long audio, real casualty, production identity, packet capture, actual crash or distributed resource-budget acceptance. Existing self-reported role limitation remains. No hard cancellation or automatic unknown recovery. No model confidence/accuracy guarantee: observed silence hallucination is a concrete limitation, not hidden. Audio archive/restore still unsupported409; no merge/deploy/push in this turn.
