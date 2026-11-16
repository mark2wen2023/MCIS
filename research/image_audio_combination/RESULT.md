# Frozen image/audio candidate combination

Inputs: image 91962113bd98778d3538f0e8e9879a014023c21f; audio cc0cdc76beea9e11578e6277aa7cfc297f7b238c. Common base 94d5e38c926fda232bb987b60fa9145e4bcf01a7. Independent integration branch; main untouched.

Actual merge conflicts ONLY REQUESTS.md and ROADMAP.md. Verified both inputs begin with common-base bytes, retained full audio content plus full image append region; added this integration record afterward. All 126 non-overlapping changed input files exactly match their corresponding input blobs; input-sha256.txt freezes them. No runtime edits beyond combining approved candidate source trees, no shared app factory/route, installation or model execution introduced. Historical freeze files retain their commit-specific meaning.

4 new individually reviewed ordinary synthetic tests passed in 3.09s. Image and audio separate app instances share one temporary SQLite/settings and synthetic case; imported fabricated OCR and ASR drafts, not actual inference. Synthetic PDF/page bytes are fixture placeholders, not parsed real pages or previews. PCM generated in fixture. Tests cover independent human edits and original draft preservation; combined audit chain and event counts; separate factories reopening histories; mixed-case export 409/no ZIP/no partial record changes; distinct optional routes and default app absence; both runtimes None and task starts 503. No browser, paused/security/write-refusal test or old test node executed.

Exact command:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_image_audio_combination.py::test_shared_database_preserves_independent_revisions_and_audit service/tests/test_image_audio_combination.py::test_independent_factories_reopen_same_histories service/tests/test_image_audio_combination.py::test_mixed_case_export_refuses_without_partial_package_or_record_changes service/tests/test_image_audio_combination.py::test_no_unified_default_routes_or_implicit_model_runtime --tb=short
```

Limits: this is source-tree combination and selected ordinary compatibility testing, not full-suite/product/SSO/model/browser acceptance. No simultaneous OCR/ASR subprocess scheduling, real crash, old deployment migration, concurrent app transactions or full mixed-media restore verified. Runtime-model dependencies and local public samples remain environment-specific. Audio v2 archive assembly remains audio-only; mixed image/audio and other unsupported content must keep refusing. No formal export/restore enabled. No old PR/branch closed, no deployment or main merge. Independent review pending.
