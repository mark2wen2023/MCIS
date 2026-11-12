# W10.2 independent acceptance: PASS

- v2 frozen implementation: 12/12 hashes matched before and after.
- 45 integrated independent scenarios passed, 0 failed: 37 HTTP/storage and 8 real Chromium. Original 43 assertions/scenarios retained, plus 2 real HTTP W8.4 metadata cross-package tests.
- D01 closed by retained original failing assertion plus missing/modified point, source and epoch recovery checks.
- Actual HTTP, synthetic fixtures in two fresh databases, actual Chromium at desktop widths 1440/1920, local loopback only.
- Original CSV BOM/CRLF bytes, reports, digests, persistence, permission changes, concurrency, fault rollback, fresh-database .mcase roundtrip, response-loss recovery and navigation isolation covered.
- Large preview: 10000 rows, 100 samples, 20 DOM rows per page; observed preview time 0.284 seconds on this integrated run, not a general performance guarantee.
- No implementation source changed by acceptance; no implementation self-tests reused; no install, deployment, model call or real user data.
- Scope is the fixed MCIS-UTC CSV v1 first-track slice only. Does not certify arbitrary AIS/NMEA, cleaning, interpolation, full W10, crash ACID, multiworker concurrency, mobile/accessibility completeness, or all exact budget boundaries.
- Reproduction: see tests_acceptance/W102/README.md; configure MCIS_BROWSER_BIN to an already-installed compatible browser.

Details and historical red/green disposition: DEFECTS/W10.2.md.

## W8.4 integration verification

Integrated baseline: main 7c1208daef26fd263b87edd9d06bab3d6b267725.
Description-only title/summary edits between W10 preview and commit preserve epoch/digest and allow the original confirmed request. Description edits after saving preserve receipt, source/report bytes and all track-point objects; original request remains idempotent. Both tested through actual W8.4 HTTP PATCH contract.

Latest 45-scene evidence: logs/w102-independent-integrated-final-run.log, logs/w102-independent-results.json, logs/w102-independent-integrated-hashes-start.txt and logs/w102-independent-integrated-hashes-end.txt. The original 43-scene v2-final-run.log remains unchanged. Both integrated start/end freeze checks: 12/12.

W8.4 preservation was independently verified by 20 checks: 6 nonshared backend + 10 UI frozen hashes, exact whole-file W8.4 hashes after removing only W10's two main.py lines / four schemas and five OpenAPI paths, and metadata GET/PATCH retained in both contract and runtime OpenAPI. Evidence: logs/w102-independent-w84-preservation.json. The coordinator's separate original W8.4 run is 42 behavior + 4 contract passes and 1 expected old shared-file-freeze failure, not 47 green; its assertion/freeze remains unmodified.
