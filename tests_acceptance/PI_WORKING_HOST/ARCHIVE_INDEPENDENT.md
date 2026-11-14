# Independent Pi working-history v2 review

Scope: Pi result validator, current-source save/export checks, v2 supplemental
archive with legacy v1 import, review-origin provenance and fixed-scope RPC.
Native independent subtask; no real model/API, no web edits, no commit/deploy.

## Finding and correction

An impossible trace with read/validation tools before its first model cycle was
initially accepted by the archive shape validator. Reproduction was supplied and
the implementer added a completed-model prerequisite for tools and a model-end
immediately before final. The reproduction now rejects before import writes.

## Final checks

`test_pi_archive_independent.py`: **15/15 passed**, zero skips, 19.60s.
Updated historical tests (`test_pi_working_probe_independent.py` and the Pi v2
archive test in `test_pi_working_independent.py`): **5/5 passed**, zero skips, 5.50s.
One existing Starlette TestClient deprecation warning only.

Verified with actual SQLite and mocked model responses:
- malformed trace, latest failed validation, missing/duplicate final, unknown
  fields and false review-origin authority claims reject without archive writes;
- import and historical read have separate grants; imported Pi records remain
  untrusted/inactive and do not change active working proposals;
- source changes deny current export; already-imported historical read remains
  explicitly unverified rather than inheriting current-source authority;
- legacy v1 roundtrip preserves absent review origin as unknown;
- legacy operation replay does not rewrite old origin, and new origin changes
  conflict under the same operation ID;
- RPC refuses caller-supplied reviewOrigin, while projecting server-stored origin;
- current-source validation rejects changed output digest, source scope or span;
- scripted rehearsal explicitly passes scripted_test, not a human-review claim.

## Deliberate trust boundary

Imported outputDigest is a historical claim with checked hash shape. Its original
sourceDigest cannot be reconstructed without original sources, which this
supplemental archive intentionally excludes. Recomputing the outer checksum
therefore does not authenticate imported claims. A deliberately changed historical
outputDigest remains importable but historicalClaimsVerified=false and
activated=false; this is explicitly tested, not claimed as authenticity.

The earlier unsupported-Pi-export limitation is superseded by v2 support here.
This still is not a full case/original-media backup, signed audit, human identity
attestation, real model accuracy test, UI acceptance, CI or deployment.
