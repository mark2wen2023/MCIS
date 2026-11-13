# Internal unreviewed run save: verified local results

- Implementation25/25 passed, zero skipped,14.40s, including one actual rebuilt C# W2 computation on synthetic registered CSV followed by real SQLite audit/index persistence.
- Independent32/32 (25 implementation+7 independent), zero skipped,16.85s; frozen8-file hashes checked before/after.
- Final selected regression136/136, zero skipped,55.73s: internal save, strict historical schema, historical read boundaries, source/case incarnation and package/archive tests. MCIS_PREFLIGHT_REAL_CORE supplied the already-verified executable wrapper.
- Actual W2 DLL SHA256657e99512fb9c42eb900fb1acb9bca5474ece49873b5ca74c78f3eb98355af41. Processing records persist fixed service/adapter/core protocol labels, not an attested executable version. No executable path/secrets included in records.
- Independent finding fixed: operator U+0085/U+2028/U+2029 could break audit physical lines and export; now rejected before compute, along with invalid UTF8 surrogate. Scope actor frozen across calculation.
- First broad run127 passed/2 failed because older tests expected no unreviewed table at all. Updated only the historical nonactivation assertion to require zero index rows now that the schema exists. Final136 run passes; imported history is not activated.
- Two independent-session concurrent same-operation tests, changed request conflicts, commit/audit/index/budget failure rollback, stale/revoked replay refusal, discarded response recovery, index corruption and full historical roundtrip covered. Core controlled in failure/concurrency tests, real core only in the explicitly identified positive test.
- No external API/UI/approval/production authentication, live LLM, browser/CI/deployment claim. Package support/budget/default-policy restrictions remain; internal save is not unlimited archival capacity.
