# Independent supplemental archive RPC review

Reviewer: catalog_review. Product authored separately. Reviewer changed only its uniquely named test file and this report. No push, merge or deployment.

## Final result

**27 passed**, one dependency deprecation warning, 30.16 seconds.

```
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_archive_rpc_catalog_review.py
```

## Blocker reproduced and repaired

Initial independent run: 1 failed, 20 passed. Export checked live bindings twice before constructing the final response, but a source binding change during response projection was followed only by case/session authorization, allowing a stale bundle to escape. The implementation now makes its final content operation a fresh live export and exact-byte comparison after projection and scope authorization. The original failing test passes in the final run.

## Coverage

- Live source changes after worker and during final projection reject export without body.
- Import commit followed by projection error yields unknown (503), not an assertion of rollback; identical retry is replayed and one import exists.
- Import grant revoked after commit yields unknown; subsequent retry is denied without another import.
- Read grant revoked during projection withholds the response body.
- Closure after committed worker withholds body and reports unknown.
- Cancellation after commit propagates cancellation; original retry remains one replayed import.
- Same request ID cannot change payload or action; 64-entry budget rejects new IDs while original retry still works.
- Changed case/context/profile, legacy role/path/extra fields, nested/nonstring values, invalid/noncanonical Base64, malformed digest and oversized bundle reject without save.
- Deep JSON, nonfinite JSON, duplicate JSON keys and raw data exceeding 8 MiB never save.
- Fixed target epoch cannot silently rebind.
- Explicitly authorized historical read survives live-source changes and remains inert/unverified; live export is denied.

## Boundaries and limitations

This is local Python testing, not CI or production authentication/end-to-end browser certification. RPC permits only fixed-scope archive operations; credentials, filesystem paths and legacy identity headers are not client input. Supplemental archives are not complete backups. Imported content, author and source claims are unverified and do not activate evidence, rights or facts. The fixture remains synthetic and per-process temporary, not real LLM inference or cross-process persistence. UI/file/download checks are reviewed separately by the parent/UI worker and are not counted here.

## Frozen SHA-256

- working_archive_rpc.py: `93d3b3e472c0d44a88b349e0d0175708e625b7a5bcde1c4fa36c26f92bdd41dd`
- working_archive_fixture.py: `227f3bcc6544f7bcffee90047eac11bff0e53f6e0f492854ee0c36918e4c3186`
- test_archive_rpc_catalog_review.py: `a1d8ce7dba47a7295efa9b128031ee84b0bfbb2f0802e86fd987a597570904be`

No remaining blocker identified in this bounded backend slice.
