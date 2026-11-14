# Exact AIS sample preservation independent review

PASS for the minimal state_at exact-record branch. **14 passed in 1.21s** (10 author + 4 independent); one TestClient deprecation warning. No implementation or remote changes by reviewer.

Independent tests (`test_independent.py`): duplicate final timestamp returns the first recorded exact match while existing after-end behavior still returns the last listed point; exact sparse record does not demand interpolation-only fields; top-level result mutation cannot change original sample; actual GET tracks stepSec route with real ORM synthetic rows preserves recorded metadata at first/interior/last sample and leaves stored rows unchanged. Nonexact resampling still labels Interpolated.

## Important contract limits
state_at now returns dict(b) at exact b.timeSec, preserving all fields of that recorded sample instead of synthesizing interpolation metadata from a. The copy is SHALLOW: nested extra metadata remains shared; no new deep-copy guarantee exists.

Actual GET tracks still deliberately recomputes utc using case epoch and returned timeSec. Therefore helper-level exact UTC preservation must NOT be described as byte-for-byte preservation of every API output field. Tests verify API equality excluding utc and explicitly verify the existing UTC recomputation. No database record is rewritten.

Duplicate timestamps are not conflict-resolved: first encountered wins for exact match; outside the track's end the existing last-point clamp remains. SQL duplicate-order determinism, malformed/unsorted tracks, long-gap interpolation correctness, source provenance beyond recorded metadata and real navigational conclusions are not changed or certified.

This is synthetic deterministic API/unit/COLREG-call coverage, not real AIS case acceptance, LLM testing, full CI, browser, deployment or proof of repository Git ancestry. Do not push reconstructed synthetic history on the strength of these tests.
