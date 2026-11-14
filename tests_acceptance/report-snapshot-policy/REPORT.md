# Report snapshot policy regression repair

Latest fetched main25b9df6e1e8c554b043547afc9cd298eb4a5ff6e; independent branch
fix/report-snapshot-test-policy directly starts there. Timeline remote
integration/timeline-main-25b9df6 remains efc1dd8eb1b50fc4c0301b360a44bc8ccec984e8;
GitHub query found no PR whose head is that branch. It is not merged into main
or incorporated here. No changes to its code or remote branch.

Fresh baseline test_reports_w161_snapshot.py:11 failed,3 passed in2.84s.
Investigator context fails existing full-content policy before snapshot creation
or lookup. Thus the old role-only success expectation and missing404 assertions
were not aligned with current policy. The source require_content checks both
category levels and applicable field rules; no new permission grant is needed.

Only this test module changes. Synthetic handler context now uses LeadInvestigator
for full-content snapshot lifecycle. Both investigator-role cases remain:
Lead retrieves the complete expected report; Investigator must receive403 for
known and absent snapshot references. A separate cross-case-reference403 test
and existing restricted-role cases verify unchanged database table snapshots.
Allowed Lead missing/cross-case404 tests remain. No global fixture/policy/renderer
or authentication edits, no fake SDK results, no test skipped.

Full original audit JSON byte compatibility assertions stay Investigator-valued
and unchanged. Long reason whitespace/full text, before/after values, exact
snapshotRef, schemas, audit linkage/valid chain, read repeatability and legacy
snapshot reference without audit-line rewriting all run under allowed context.
Before/after hashes use the existing helper reading all SQLAlchemy metadata
tables; this proves those rows unchanged in these sequential tests, not filesystem
atomicity or concurrent revocation. Direct handler tests do not prove HTTP response
headers or real SSO. The related HTTP access suite is reported separately.

Self-tests15 passed in3.90s (after.txt), baseline log retained with trailing
whitespace normalized only. Independent results recorded separately. No full
repository suite, browser, AIS or real HFACS execution was claimed. Existing
real identity, long-lock, memory, missing SDK and browser gates unchanged.
No SDK installation/download, remote push, merge or deployment in this task.

Related test_reports_w162_access.py HTTP/policy suite:80 passed in12.68s
(related.txt), not a full-service result and not additive to independent reruns.
