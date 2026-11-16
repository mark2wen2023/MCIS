# Explicit isolated image/audio review demo factory

Parent 22f0112f39be8e95fb6e50573660a022b7f12b12; continued integration/image-audio-candidates. No default main application edit or server started.

## Code
Extract register_image_review/register_audio_review from existing app factories. Original factories delegate while retaining their signatures and explicit-runtime capability. Duplicate registration on an already registered app raises before adding routes. Existing table initialization, triggers, permission handlers, source downloads and pages are preserved. New mcis_service.media_review_demo.create_media_review_demo(settings) constructs the base app once and registers both modules against the same db/settings. It has no runtime or enablement arguments and leaves both runtime slots None. No extra combined page or navigation, no model execution/download/installation. Original separate factories remain optional entry points.

Caller must supply a disposable isolated settings/database/blob directory. The factory does not independently prove directory isolation or provide an OS/network/security sandbox. Default main app does not import/mount the demo. Explicit host-side mutation of app.state is not prevented by Python; runtime defaults are not an authorization/security guarantee. No production authentication changes. Existing product archive refusal unchanged.

## Developer ordinary tests
5 individually reviewed NEW synthetic nodes passed in 2.30s. Same-app imported fabricated OCR/ASR drafts, generated PCM, temporary SQLite, human edits, original text retained, shared audit chain/action counts, reopened histories, distinct routes registered once, default app unmounted, no runtime arguments, unconfigured task503, mixed export409 without ZIP or state changes. Original separate factory explicit-configuration compatibility uses an inert object and never dispatches.

Page GET200 is a TestClient response check, not browser/JS/render/interaction verification. Existing test helper functions reused only; no historical test nodes, full files/suites, paused/safety/write-refusal/browser tests executed. No actual OCR/ASR or real source documents used. Concurrency, crash, old deployed migration, real identity and production readiness unverified.

Exact command:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_review_demo.py::test_same_app_edits_audit_and_reopen_preserve_both_histories service/tests/test_media_review_demo.py::test_demo_routes_once_and_default_app_still_unmounted service/tests/test_media_review_demo.py::test_demo_has_no_runtime_arguments_and_both_tasks_unconfigured service/tests/test_media_review_demo.py::test_demo_mixed_case_refuses_export_without_partial_state service/tests/test_media_review_demo.py::test_original_factories_keep_separate_routes_and_explicit_configuration --tb=short
```

Prior input-sha256 freeze remains correct at22f0112; the two app.py files now intentionally differ by registration extraction. New logs/media-review-demo-impl-hashes-frozen.txt identifies this change. Formal export/restore remains blocked; source completeness, task logs/HOME, writer closure and publication remain unresolved. Independent review pending.
