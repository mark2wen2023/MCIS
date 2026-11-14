# Independent working-history supplemental archive review

Reviewer: independent catalog_review subagent. Product changes were made by a separate implementation agent; reviewer edited tests/report only. No push, merge, deployment or real LLM call performed.

## Result

Final local independent suite: **33 passed**, one dependency deprecation warning, 30.50 seconds.

Command:
```
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_working_archive_review.py
```

No remaining blocking finding identified in this bounded slice. This is not CI, browser acceptance, production identity validation, full backup restoration, or a claim that historical facts/authors/model identity have been authenticated.

## Security regression found and resolved

The independent final-epoch-read test initially reproduced an authorization ordering defect: expiring the current session during the final case metadata read did not prevent import commit. Implementation now repeats policy/grant checks and terminates with session authorization after reading that metadata. The exact regression test passes in the final 33-test run, and import rolls back.

## Independently exercised boundaries

- Original draft proposals, fixture flags and both human review versions retained; no live proposal/review updates.
- Actual empty target database with a different incarnation accepts same-case historical import. No live proposal, review, working grant, interview or source incarnation created.
- Independent canImport/canRead permissions, default denial and revoked-session read/list/replay denial.
- Changed live interview/source context blocks live export without incorrectly preventing explicitly authorized inert historical reading.
- Changed target epoch hides listings and rejects historical read/replay.
- Import grant revocation and final session expiry roll back; synthetic commit failure leaves no import; retry can succeed.
- Rehashed malformed packages, incompatible claims, duplicate proposals/JSON keys, nonfinite JSON, deep nesting and raw-size excess reject.
- Validly shaped fabricated author UUID remains only an unverified historical claim; no authenticated subject provisioned.
- Source declaration scope mismatch, missing registered declaration, malformed IDs/UUID/hash and extra keys reject.
- Validly shaped fabricated registered-source declaration remains unverified, does not activate any source or create a source row.

## Explicit limits

SHA-256 is content integrity, not a signature. Imported authors, source identities, binding claims, model outputs and timestamps remain historical/untrusted. Original evidence bytes and full interview records are not included. Current target access requires explicit archive grants plus current full-content/testimony policy; old source existence is deliberately not a prerequisite for reading an authorized inert historical copy. Production login, external transport, UI and full-system end-to-end behavior are outside this suite.

## Frozen SHA-256

- `service/mcis_service/agents/working_history_archive.py`: `38ddad108639cf6724339c3c38ef436cd6056745b8ae0154d6f9ed84a4452f14`
- `service/tests/test_working_archive_review.py`: `d6e51f91a09a9180408ab0df35f3cdcbe1d9174f51c9090b9f0bb4cabe903839`

Test filename is unique to this reviewer. Parent transaction tests are maintained separately and are not counted above.
