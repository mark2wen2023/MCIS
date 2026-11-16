# Fresh isolated demo preparation

Parent 567bee70b9afbd18b09b84628533fb86eb3ecfde. tools/media_review_demo/prepare.py creates a new mkdtemp child on every invocation, never accepts an existing DB/root, explicitly sets data_dir/db_url/seed_demo=False and uses only existing case/intake/review APIs through in-process TestClient. No direct ORM insert, model inference, subprocess, server/browser startup, download or deletion. Failed preparation retains its new directory and marks incomplete; no in-place retry/cleanup. This does not promise file/DB crash atomicity or solve uncertain commits.

Default materials are valid generated schematic PDF/PNG and a 440Hz tone, fabricated OCR/ASR drafts labelled synthetic and pending. They are not speech/report recognition. Page mapping remains declared, unknown transcript times/speakers remain unknown. Current extraction timestamps describe preparation of local demonstration copies, not historical capture time of upstream evidence. Case time/location are explicitly synthetic placeholders.

Optional public audio requires all three explicit files and pinned byte hashes: FunASR sample a1bd32dc78493c123f9625a66deee562aed2895f53fbc39f2cca3be7e6f4f20f, upstream repository MIT license f382b62dcc61fc566b9215b1e3b604b539bfd96ed52ae1eeff5090f6dc176057, saved local SenseVoice output1642c59d687568c5cbf9e6dc59b0c2fc20405d48d0253206f5935f79c23d63c2. Source: https://github.com/modelscope/FunASR/blob/c1e3018bf0b16ac10d40fe7cf902cafd624ee4dd/runtime/funasr_api/asr_example.wav . Local license and provenance records were reviewed; no fresh online provenance/license verification this round. Missing/mismatched files stop before new directory creation. License and raw saved output are themselves registered through intake. Result is rebound to the new registered source by existing converter; original audio bytes unchanged.

Image report reuse permission was not sufficiently established by available local manifest (public landing-page provenance is not an explicit reuse license). No real report is imported by this script; generated schematic is the explicit fallback.

## Actual executions
First three new synthetic nodes: 2 failed /1 passed because extraction timestamp was fractional-offset rather than required whole-second UTC Z. Corrected script formatting, without relaxing intake; rerun 3 passed in1.65s. Fourth new digest-mismatch node passed. Four unique new ordinary nodes total, not a full suite. No paused/security/write-refusal/browser tests. Tests verify API readback, hashes, valid format signatures, separate new directories, environment DB/seed override and missing/mismatch stopping. No human listening or image rendering verification.

One actual preparation (not a model run) consumed pinned public WAV/license/saved output plus generated image assets: /workspace/mcis-media-demo-y3dt6y3l ; case MEDIA-DEMO-SYNTHETIC ; image run OCR-e7f9504c4b19464fb36feae221ce527b ; audio run AR-f2b029dee11c4abeb5d43482b7e5d09c. Both review GETs succeeded before status prepared. This is developer execution, not independent acceptance. Runtime emitted a Starlette/httpx deprecation warning; no dependencies changed. Generated media/DB stay outside repository.

Exact test commands (first repeated after correction):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_demo_prepare.py::test_fresh_preparation_reopens_pending_image_and_audio service/tests/test_media_demo_prepare.py::test_each_run_uses_new_directory_and_ignores_database_environment service/tests/test_media_demo_prepare.py::test_missing_public_inputs_stop_before_preparation --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_demo_prepare.py::test_public_digest_mismatch_is_not_treated_as_verified --tb=short
```

Usage from repo root, existing dependency environment only:
```
PYTHONPATH=.:service python tools/media_review_demo/prepare.py --parent /workspace
# Optional known local public audio; never runs the model:
PYTHONPATH=.:service python tools/media_review_demo/prepare.py --parent /workspace --public-audio /workspace/mcis-sensevoice-trial/sample/asr_example.wav --public-license /workspace/mcis-sensevoice-trial/sample/LICENSE --saved-result /workspace/mcis-sensevoice-trial/timestamp-result.json
```
The actual interpreter used was /workspace/mcis-pr104-supported-archive/service/.venv/bin/python. CLI reports newly created directory, case/run IDs, receipt and byte hashes. To view later, explicitly construct create_media_review_demo with that directory's demo.db and seed_demo=False; never use default Settings/environment paths. No start launcher added or executed. Permission model remains existing role headers, not SSO. Formal export/restore remains unsupported; extra raw/license evidence is preserved and must not be silently omitted. Independent review, browser, concurrency/crash and production acceptance pending.
