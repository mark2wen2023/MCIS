# Independent report snapshot policy test review

Verdict: PASS for the scoped test adjustment on main25b9df6. Read AGENTS.md/handoff, complete module/diff, snapshot handler and snapshot_db helper. Product service/contracts/web diff against HEAD is empty; only the local test context and role assertions changed.

Fresh independent execution:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_reports_w161_snapshot.py
sha256sum -c logs/report-snapshot-policy-impl-hashes-frozen.txt
```

**15 passed in3.78s**, independent-tests.txt; frozen test hash1/1 matched, independent-hashes.txt. Coordinator baseline.txt inspected:11 failed/3 passed in2.84s. That baseline was not independently rerun here.

The module-scoped ctx fixture now uses LeadInvestigator so original snapshot-business tests reach existing content checks; shared fixtures/service permissions remain unchanged. The former Investigator success assertion is explicitly changed to403 under current full-content policy, rather than removing that role. Lead success remains, restricted ExternalExpert/InterestedState/AgentService/Public tests remain, and Investigator known/missing/cross-case-reference denials are checked. Existing handler orders content and audit permission before snapshot lookup, supporting403 even for missing references. A cross-case row is synthetic trusted test setup, not a claim of a remotely exploitable cross-case write.

Original long-reason and original/new text preservation, full snapshot fields/schema, snapshotRef/audit links, repeat-read stability, byte-identical legacy build_line, legacy audit-line preservation/valid chain, authorized missing/cross-case404 and real-case read-without-write cases remain. No substantive snapshot business assertion or parameter was deleted; the intentional Investigator permission expectation change is explicit and justified by unchanged service policy.

New before/after hashes use all Base.metadata tables with existing snapshot_db, covering database rows in these sequential tests. They are not filesystem snapshots, concurrent crash proofs or database-independent integrity guarantees. All calls are direct Python handlers with synthetic contexts and real local SQLite, not HTTP transport, no-store/header checks, or authenticated SSO. No real C# core is claimed or mocked, and unrelated environment failures are not suppressed.

No frozen implementation changes by reviewer, commit, push, merge or deployment. Focused test alignment passes; broader integration acceptance is outside scope.
