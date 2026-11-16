# Developer evidence, not independent acceptance

Parent cf9e78d4fecda93d48e85d273dcbcd670b53d706, separate candidate/audio-sensevoice. It does not include paused faster-whisper converter edits from the other worktree.

## Ordinary code tests
```sh
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q service/tests/test_audio_review_candidate.py service/tests/test_audio_sensevoice_candidate.py --tb=short
node --test tests_acceptance/audio-review-candidate/page.test.cjs
```
20service tests pass (13inherited+7new); 4synthetic-DOM tests pass. The latter are not browser testing. New fixtures fabricate PCM silence and recognizer records, explicitly labelled in code; they are not actual ASR. Cover exact88747/16000s clock, old v2 compatibility, no original change, null unknown time, invalid rounded endpoint rejection, append-only human history, empty output rejection, timestamp length/shape/zero-duration/bounds and no promotion to location. Prior source/archive/restart/CAS/fault rollback tests retained. No prior restricted security/ECFC/browser suite invoked.

## Actual local model run and public-sample integration
Official FunAudioLLM/SenseVoiceSmall revision3847d57b6bdf2dd8875cb1508d2af43d80a16bf7. model.pt936291369bytes SHA256833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea. Official model-license1.1 source retained. CPU4threads, FunASR1.2.6, torch/torchaudio2.6.0+cpu, numpy1.26.4; pinned environment and installation URL/hash reports in /workspace/mcis-sensevoice-trial.

Public sample: modelscope/FunASR commitc1e3018bf0b16ac10d40fe7cf902cafd624ee4dd runtime/funasr_api/asr_example.wav; upstream MIT license and runtime/java/readme.md reference retained. Original SHA256a1bd32dc78493c123f9625a66deee562aed2895f53fbc39f2cca3be7e6f4f20f;88747frames at16000Hz, duration5.5466875s. No modification/upload. Actual original run text matches upstream reference, not independent listening. Timestamp-enabled actual run retained19pairs with no words field; final pair4770–5550ms exceeds exact duration, so draft is unlocated. All tags/pairs retained, no claimed emotion/fact/identity.

Commands and runtime artifacts outside Git:
```sh
/workspace/mcis-sensevoice-trial/venv/bin/python /workspace/mcis-sensevoice-trial/run_timestamp.py
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python tests_acceptance/audio-sensevoice/run_public_sample.py /workspace/mcis-sensevoice-trial/sample/asr_example.wav /workspace/mcis-sensevoice-trial/timestamp-result.json /workspace/mcis-sensevoice-trial/candidate-link
```
Public integration PASS: real FastAPI TestClient/tempSQLite/intake -> exact sampleSource -> convert real saved output -> importv3 -> append human-input revision -> unchanged original download -> restart same history; export409 preserved. Manual input is developer reference-text comparison marked pending, not actual listening or approved transcript. Result: /workspace/mcis-sensevoice-trial/candidate-link/result.json. This command consumes saved real output; it does not itself run the model. No mock success response substitutes for backend integration.

No actual browser, audio player behavior, independent review, product/default-route rollout, production authentication, crash safety or archive restore validated. No media/model/database included in this branch. Model/source downloads and environment remain local. A runtime dependency install is not application deployment.

Exact local timestamp runner is copied here as run_timestamp.py (fixed isolated paths); SHA matches the actual executed runner. It is not imported by tests and never runs in the default product. requirements.lock, dependency-sources.json and model-files.json preserve dependency/model identities; model weights, sample and output are not included. Install from the documented official indexes only, in an isolated environment.
