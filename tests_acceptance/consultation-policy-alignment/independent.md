# Independent consultation input/policy alignment review

Verdict: PASS for this test-only alignment on direct parent main73fc800. Read AGENTS.md and handoff, complete test diff and existing consultation routes/whitespace checks. Product service/contracts/web diff is empty. The sole frozen implementation change is service/tests/test_consultation_input_w73.py.

Fresh independent execution:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_consultation_input_w73.py
sha256sum -c logs/consultation-policy-alignment-impl-hashes-frozen.txt
```

**20 passed in12.33s**, independent-tests.txt; frozen hash1/1 matches, independent-hashes.txt. Coordinator baseline.txt retains15 failed/2 passed in4.91s; inspected but not independently rerun here. This focused result does not classify or resolve all existing service failures.

The existing routes already require full-content policy for reads and full-content plus report_draft ReadWrite for writes. Switching authorized business-input cases and fixture preparation to synthetic LeadInvestigator reaches those existing validation paths without weakening service policy. No shared fixture, production route, core implementation, skip or mock changed.

Original assertions and parameter sets remain: bad open422/code with unchanged state/audit; exact identifiers and nonblank text preservation; existing open/closed/missing-round error precedence; Public/InterestedState permission-before-business-error checks; blank waiver rejection without writes; empty structural error; five non-.NET-whitespace values preserved; explicit Python whitespace set. HTTP statuses are now checked before successful response parsing. Existing round cleanup still performs explicit authorized waiver/close operations rather than deleting seed data.

Snapshot now fetches rounds and audit as Lead, requests the full2000-item audit page and verifies chain validity/count equal to returned events. The equality assertion prevents silently treating a truncated page as complete for these fixtures. Three added role cases (Investigator,Public,InterestedState) each test list/open/waive/close403 FORBIDDEN and no-store, then compare before/after rounds plus full audit. This is a tested response/audit snapshot, not a universal all-table rollback proof or recursive leak audit. Other consultation routes are not newly covered by these three cases.

No original business assertion was removed or weakened. The test docstring correctly limits role headers to synthetic policy tests and whitespace parity to Python checks; this does not execute or validate real C# core, establish SSO, or repair missing HFACS SDK. Existing core/environment failures are not skipped or hidden by this patch.

Reviewer changed only acceptance/disposition artifacts, not frozen implementation. No commit, push, merge or deployment. Broader integration/browser/core acceptance remains outside this narrow pass.
