# Versioned report + timeline candidate (API only)

Base: origin/main f2eff95dfb1bbf6afd92036ec589a1513f0b8840; isolated branch feature/report-timeline-archive-v1. No deployment/merge. Contract: contracts/report-timeline-archive-v1.md plus timeline-records-archive schema. Frozen implementation list: logs/report-timeline-impl-hashes-frozen.txt.

## Implemented behavior

Working-record v1 cases with timeline rows produce outer1.4.0 and a mandatory timeline/records.v1.json extension. Key, exact original document, createdUtc and updatedUtc are retained. The old analysis/timeline.json is a checked mirror, not a second authority. Import validates version/case/row identifiers, duplicate IDs, bounds, timestamps, existing API millisecond UTC semantics, end-time order and same-package evidence/vessel references before mutation. It restores rows in the existing transaction; legacy import cannot consume the new extension without validated working state. Re-export preserves original source package bytes, original audit prefix and timeline metadata through three stores.

Only timeline_events has a conditional working-archive exception, paired with a dedicated serializer, validator and restorer. All other unknown/populated state still refuses. Timeline plus track-import history is intentionally rejected (1.4 requires workingv1); old1.0–1.3 branches retain meanings. Recommendations, consultation, conflicts, COLREG, agent and other unsupported states remain blocked. A report citation to an unsupported registered source remains blocked by existing closure validation. Imported confirmed/sourceLabel values remain unverified historical fields; no new confirmation or UI historical badge.

Full-content policy applies before archive bytes and under the existing SQLite writer reservation. The new concurrent test uses actual second-connection BEGIN IMMEDIATE: revocation waits while export holds the reservation, then commits and the next export403. This establishes the tested transaction order, not a promise to retract bytes already approved/committed or sent. Role headers are still untrusted; no production SSO claim.

## Verification

Final focused command:

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests/test_report_timeline_archive.py
```

**26 passed /12.38s**. Tests include actual HTTP handlers/SQLite, three-store exact-row/report/audit/source-package preservation, source-linked evidence bytes/hash, two legal submillisecond values, cross-case/missing/duplicate references, wrong/missing/unknown versions and members, mirror conflict, empty/257-row extension, malformed timestamp, legacy-entry refusal, unknown recommendation state refusal, denied role, actual concurrent revocation ordering, and explicitly injected post-restore failure proving database snapshot and destination-directory rollback. Fault injection is labeled; there are no model mocks or model capability claims.

Initial broad regression:135 passed/1 failed in39.88s; separate track-history33 passed/1 failed in17.50s. Both failures require unavailable HFACS .NET core. Each same node was rerun on the unchanged main product in /workspace/mcis-archive-unsupported (local research-only commit123b95c, product identical to f2eff95), reproducing HFACS_CORE_UNAVAILABLE:1 failed/1.10s and1 failed/0.78s. This is targeted parent evidence, not a whole-parent-suite run. Final frozen combined regression: **171 passed, 2 failed /60.11s** (final-regression.txt), with exactly those two HFACS nodes failing. Full repository tests were not run; historical180 failures104 errors remain outside this scoped result.

The frozen independent result is recorded separately under tests_acceptance/report-timeline-independent; development success is not substituted for independent acceptance.

## Limitations

Current web package-intake model deliberately rejects1.4.0. No browser/UI wiring was changed or tested; this is a reviewable server/API candidate, not a completed workbench flow. Existing long writer lock, cumulative archive memory budgets, shared service identity boundary and filesystem publication/crash/unknown-commit limitations remain; no performance or crash-atomicity claim. This is not universal case backup, source authentication or restored workflow approval. No new automatic retry or deletion mechanism.

Stored development console logs normalize trailing whitespace only.
