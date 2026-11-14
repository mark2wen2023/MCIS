# Independent source snapshot comparator review

Reviewed the standalone `freshness.py` callable and `contracts/knowledge-source-freshness-preview.md`. No implementation modifications, repository operations, network, model calls or database writes performed.

## Verification

- Added `service/tests/test_knowledge_source_freshness_independent.py`: 27 independent synthetic protocol tests.
- Primary 33 + independent 27: **60 passed**, local Python/pytest, not CI.
- Command: `../line-dataset-1615/repo/service/.venv/bin/python -m pytest -q service/tests/test_knowledge_source_freshness*.py`.
- Implementation SHA256: `bcd71f17c353b69926474b34695ab0e42d2072047000069b82026e6708d4f68b`.

Coverage: every Public source field missing on either side fails closed; required envelope fields; non-JSON/unicode values; aggregate budget; exact sorted differences; input nonmutation; no source body/private candidate field echo; socket/DNS calls prohibited during preview; unavailable observations; older snapshots and explicitly null capture times preserve unverified status.

## Findings and boundaries

No blocking defect found within the stated pure-function contract. Required source-field omissions never return unchanged. Explicit null capture times are intentionally permitted and remain null; absent required time keys are rejected by primary tests. Equal supplied fields return `unchanged_snapshot` even if time is old or unknown. `recheckRequired=false` in that case is NOT permission to approve, a currentness guarantee, or a claim of authenticated provenance. `reviewRequired=true` and all verification flags remain false.

URL syntax/reachability, source authentication, full candidate business schema, storage access, API authentication, UI, real external source acquisition, semantic correctness and model capability are outside this slice. Caller-provided URLs remain strings, never fetched. Returned digests attest only to exact supplied content. Integration must preserve these boundaries rather than treating the utility as a publication or approval guard.
