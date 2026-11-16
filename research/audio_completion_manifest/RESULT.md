# Developer synthetic verification

8 explicitly selected new pure-function nodes passed in 0.02s. No filesystem/DB fixtures, worker, ASR, browser, paused test, write-refusal probe or security test. Independent review pending. No full-suite selection.

Exact command from repository root:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider research/audio_completion_manifest/test_protocol.py::test_complete_claims_never_grant_actions research/audio_completion_manifest/test_protocol.py::test_legacy_claims_remain_unknown research/audio_completion_manifest/test_protocol.py::test_unknown_exit_and_unclosed_writers_block research/audio_completion_manifest/test_protocol.py::test_unknown_or_pending_commit_blocks research/audio_completion_manifest/test_protocol.py::test_missing_and_extra_members_block research/audio_completion_manifest/test_protocol.py::test_task_and_audit_binding_must_match research/audio_completion_manifest/test_protocol.py::test_digest_and_size_must_match_recorded_claims research/audio_completion_manifest/test_protocol.py::test_incomplete_member_declaration_blocks
```

Tests cover consistent claims without authority; legacy unknown; unknown exit/writer closure; pending/unknown/rolled-back commit; missing/extra members; task/audit binding; size/digest disagreement; incomplete declarations. Inputs are synthetic claims, not real persisted completion evidence.
