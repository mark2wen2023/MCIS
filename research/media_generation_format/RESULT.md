# Developer synthetic tests

9 unique new ordinary nodes passed in two final runs (7 passed in 0.06s; 2 passed). Initial first-seven run failed before validation because the reused synthetic fixture returns three values, not two. Fixed new fixture unpacking; reran the same seven successfully. No prior tests executed; legacy fixture function only reused. No paused/safety/write-refusal/browser tests, real model, media or database files. Independent review pending.

Exact commands (first command ran before and after fixture correction):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_generation_format.py::test_v2_all_history_retained_without_readiness service/tests/test_media_generation_format.py::test_v1_keeps_original_meaning_without_history_upgrade service/tests/test_media_generation_format.py::test_missing_observation_member_rejected service/tests/test_media_generation_format.py::test_missing_generation_history_rejected service/tests/test_media_generation_format.py::test_duplicate_reference_and_unreferenced_member_rejected service/tests/test_media_generation_format.py::test_inconsistent_audit_association_rejected service/tests/test_media_generation_format.py::test_unknown_version_and_case_disagreement_rejected --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_generation_format.py::test_member_bytes_mismatch_and_source_disagreement_rejected service/tests/test_media_generation_format.py::test_serialized_envelope_preserves_all_members_and_links --tb=short
```
