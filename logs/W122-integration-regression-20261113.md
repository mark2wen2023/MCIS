# PR34 isolated candidate regression — 2026-11-13 03:30 UTC+8

Inputs remain main `3aba2bf03e393909c611489ae573a887087637ac` plus PR `1ad3695c4a5233ecf30a515e79a5a33bd81f92fc` candidate. This is the same partial tree described in REPORT.md, not a full checkout. All 26 candidate SHA256 entries matched after execution.

Executed with existing `mcis-w122/service/.venv/bin/python`, PYTHONPATH set to candidate service, no installation. Tests use temporary databases/TestClient, synthetic data; model tests stub completion. No real LLM, browser, .NET/NuGet, production DB, remote repository write, commit, merge or deployment.

## Actual results
- `test_recommendation_content_access.py test_knowledge_archive.py test_interview_access_w52a.py test_report_output.py`: **202 passed**, 37.17 s. See main-route-regression-0330.log. Includes original-content permission boundaries, independent knowledge archive, interview access and synthetic model-review gates, PDF/DOCX output provenance.
- `test_working_record_archive.py test_track_history.py test_archive_export_safety.py -k 'not test_report_versions_full_review_gisis_and_hfacs_coexist and not test_real_hfacs_and_report_optional_extension_three_generations'`: **90 passed, 2 deselected**, 35.84 s. See archive-track-regression-0330.log. Both deselected tests explicitly call real HFACS C# core; they were not executed. Selected process-race tests launch Python workers only.

These 292 selected passing tests are this regression batch only, not full project completion or full acceptance. Prior 88 CPA/stub tests and UI-model assertions are separate historical runs, not independently repeated here. Current real C# numerical behavior, actual browser interaction, Unity and full-tree integration remain unverified. Remote PR #34 was not updated and its conflict remains. Do not merge based on this report.
