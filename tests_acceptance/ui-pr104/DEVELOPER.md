# UI + PR104 — DO NOT MERGE / pending independent acceptance

Exact input heads: UI 139f18849b89a451cd1198635bd571c00571a579 and PR104 b4df82306d9bab87b938b9e447e27a64b0464406. Common main base 94d5e38. Inputs and tested merge recorded in inputs.json. Neither source branch/PR was modified. No new product changes.

Only REQUESTS/ROADMAP append conflicts occurred; main prefix plus both complete tails retained byte-for-byte. ReportView merged without conflict: diff against UI is exactly the PR104 inherited-citation increment (added/removed lines match). All other input files match source blobs; changed-path union and both ancestors checked. Product-side backends, provenance/export repairs, trajectory contract and CSV numbering from PR104 retained together. Prior freeze files remain historical; use this integration freeze for the combined code.

## This execution only

- 19 previously reviewed UI scripts: passed, exact commands/output in ui-results.json; no failed/skipped scripts.
- From web: node tests/ui-pr104-inherited-citation.test.cjs: new synthetic SSR, three languages / 15 assertions passed. Visible inherited-reference notice, citation retained, source object unchanged. Initial shell command had a duplicated web/ path and could not create/load the test; corrected path passed. Not a product failure or browser result.
- From service: ./.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_report_modified_citation_disclosure.py::test_investigator_citation_notice_preserves_data_even_stale_status: 6 passed in 0.04s. Precisely this parameterized pure formatting function selected; it uses constructed sentence dictionaries, no client fixture, DB, actual public report or renderer invocation. conftest has no autouse fixture. Other file nodes were not run.
- From web: npm run build: TypeScript + Vite 8.3.8 passed, 767 modules; JS 1,862.11 kB / gzip 601.69 kB. Existing >1500 kB chunk warning. This preceded only addition of the standalone CJS test/evidence, no later product edit.

Existing installed dependencies reused, no installation. No whole-file service selection, paused node, refusal/write probe, HFACS, model, actual report material, service or browser was executed. Public-report HTTP/export tests were reviewed but excluded because they load actual public material. Existing report-render test was not run in full because it includes a refusal-response simulation; the new ordinary SSR test isolates the needed positive display contract. Counts are separate kinds of evidence and not added to historical totals.

## Remaining acceptance

This is developer integration evidence, not independent combination acceptance. Normal full parent save/reload, real HTTP/backend and production identity/permissions are NOT validated. 403 and structured GISIS errors remain static-only. Review busy-before-render, cross-page lifecycle, backend concurrency/unknown commit, archive restoration and all original group limitations remain.

Historical 558 selection belongs to 1651b98; later 560 evidence included previously paused test_native_two_revisions_inventory_is_read_only and is not a safe rerun list. Neither historical selection was run here or counted toward this result. Previous LibreOfficeDev 23-page output evidence is not Microsoft Word, browser, or this combined head's visual acceptance. No PDF/DOCX visual run, real CLI/HFACS, model, full CI or production acceptance is claimed. Source-status repair does not migrate old reports; citations remain trace context, not verified support or historical source binding. Complex archive protections remain unchanged. DO NOT MERGE or deploy until normal independent checks.
