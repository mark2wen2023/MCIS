# Per-case audio task directory observations

Base: 48deeddee216e28e6fa23628b23b9e36ec04a898. Internal isolated candidate, not wired to HTTP, product export or restore.

Developer execution: 7 passed in 2.22s. These are seven new individually reviewed ordinary synthetic nodes; no whole-file/suite selection, paused node, write-refusal/security probe, browser or actual recognizer execution. Fixture imports reuse ordinary setup only. Generated WAV and fabricated task outputs reside in temporary fixture directories, not this delivery. Independent review pending.

Exact executed command (repository root):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider --rootdir=/workspace/mcis-sensevoice-review service/tests/test_audio_job_inventory_candidate.py::test_known_job_members_match_without_granting_export service/tests/test_audio_job_inventory_candidate.py::test_absent_expected_directory_is_unresolved service/tests/test_audio_job_inventory_candidate.py::test_missing_result_member_is_not_reconstructed service/tests/test_audio_job_inventory_candidate.py::test_worker_log_and_home_remain_unclassified_unread service/tests/test_audio_job_inventory_candidate.py::test_current_raw_file_hash_is_not_historical_digest service/tests/test_audio_job_inventory_candidate.py::test_different_saved_result_is_reported_not_overwritten service/tests/test_audio_job_inventory_candidate.py::test_unconfirmed_task_does_not_read_directory_or_restart --tb=short
```

The checker uses existing intake and full-archive policy with caller-owned reserved SQLite session. It queries only this case's task and evidence registration rows and traverses only their expected job directories. It does not enumerate the global job root, read registered original files, execute tasks, repair files, delete files or write database records. Session ownership remains the caller's responsibility.

Only source.wav and raw.json are classified. The original worker normally also creates worker.log and home; these remain unclassified and therefore block consistency approval, with neither content read nor recursion. A successful two-file fixture is a limited observation, not approval of real worker directories or export. Missing/unfinished/failed tasks, missing directories/results, ambiguous registrations and mismatches are unresolved. No automatic retry or reconstruction.

Raw JSON is compared semantically with saved task raw data, task ID and input digest. Its CURRENT byte digest may differ from the saved canonical JSON artifact digest due to formatting; it is not a historical file digest or proof the file existed at task completion. Source bytes are compared with current registered digest, not independently verified historical originals.

Descriptors and before/after metadata bound this observation but do not prove an atomic filesystem snapshot or exclude all concurrent modification. No adversarial filesystem/concurrency/security tests were run. Other-case directories/global orphans, complete task provenance, audit uniqueness, and whole-case completeness are not certified by this checker; the previous component checks remain separate. A zero-task inventory is not considered consistent. Export/restore/execution/cleanup flags always false. Real identity, browser, crash recovery and production integration remain unverified.
