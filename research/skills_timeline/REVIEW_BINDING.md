# Exact source binding independent review

2026-11-13. Independent native review subtask; no implementation changes.

## Verified

- Re-ran the original 32 synthetic tests: passed.
- Added 8 independent tests in `test_independent_binding.py`: passed.
- Full discovery runs 40 tests, not duplicate imported test cases.
- Checked mixed valid/invalid entries reject the entire preview, 500/501 conflict budget, null versus non-null evidence IDs, strict recheck True, repository metadata rather than forged observation fields, output copy isolation, and locator length budget.
- Exact a/b sourceLabel matching is conservative; no fuzzy alias lookup. Non-null upstream evidenceId is rejected rather than trusted. Duplicate IDs and self-comparison are refused. Arbitrary upstream summary/value text is not returned.

## Scope and remaining limits

This is snapshot-reference binding only. It does not prove observation values belong to the source, bind original media, verify timestamps, or show the conflict is factually correct. The source repository and core are test doubles; no actual W2/.NET, permission service, browser, model or production route was executed. Trusted repository metadata remains untrusted presentation text to any later renderer and must be escaped there. The real W2 transport must verify the expected sourceLabel semantics before enabling this adapter.

No blocking issue found for this narrow research increment. Production integration and complete Skill acceptance remain pending.
