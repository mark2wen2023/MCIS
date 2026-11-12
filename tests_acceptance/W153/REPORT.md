# W15.3 Independent acceptance

## Verified result
- **29 passed: 11 standalone real-CLI tests and 18 API tests**, exclusively synthetic fixtures with demo seeding disabled.
- **Real CLI + FastAPI + Vite + browser passed**, both before and after final freeze: blank draft/unselected sources, valid direct no-barrier paths with explicit non-safety disclaimer, real unknown-endpoint diagnostic, wrong input SHA rejection, edit clearing, delayed results after edit/case/identity changes discarded. Current case header follows selected case.
- Final implementation hashes checked. The ten explicitly listed existing C# dependency files match the prior baseline, and the original mcis-core binary remains unchanged. No cold output removal/rebuild of original core, W11 integration, real-report-data tests, deployment or publication was performed by reviewer.

## API / CLI coverage
Valid preventive/recovery graph; duplicate node and edge; missing endpoint; forbidden direction; threat cycle; mixed threat-chain exit; bare top-event Validate diagnostics; core-rejected top ID; no partial construction declared valid; no client state/strength/reference injection. Construction and validation results are compared with actual CLI output, not a Python implementation or expected-result mock.

Case-scoped source listing exposes only ID/title/hash. Cross-case and policy-hidden Restricted source access denied. Role denial happens before case/payload details. Real computation followed by source/case change returns 409; permission revocation returns 403. Request digest bound to case/model/source snapshots, including Unicode; successful and rejected operations leave the entire synthetic DB row snapshot unchanged where checked. Missing executable produces 503, no fallback. Unicode 500-scalar label accepted and 501 rejected consistently.

## Review outcome and limitations
No new product defect was found by this independent pass. Intentional malformed diagrams and wrong-hash response probes are negative tests, not failures in the final implementation.

Original prototype page 14 and W15 prior defect decisions were reviewed. This slice is only a manual hypothetical Bow-tie editor and structural checker. Direct paths without barriers can satisfy project graph rules while providing no assurance of safety. Nodes remain unverified and barriers unknown; registered source metadata does not validate causal links or evidence bytes. Threat-chain constraints are project assumptions, not a legal standard. No AcciMap/STAMP, ECFC import, persistence/export, professional effectiveness/risk assessment or causal/responsibility determination is claimed.

## Reproduce
```
cd service
MCIS_DOTNET=<existing-sdk-dotnet> DOTNET_CLI_HOME=<temporary-directory> PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W153/test_cli.py ../tests_acceptance/W153/test_api.py
cd ..
MCIS_DOTNET=<existing-sdk-dotnet> MCIS_BROWSER_BIN=<existing-headless-shell> python tests_acceptance/W153/browser_real.py
```

Publish REPORT.md, test_cli.py, test_api.py, browser_real.py, server.py and verified-impl-sha256.txt only. PLAN.md is preparatory; local-* raw logs and caches are not publication artifacts. Reported success is this bounded acceptance scope, not full-repository regression or complete professional analysis.
