# Ordinary report functional-test authorization fixtures

Independent branch fix/report-functional-test-policy, based directly on complete main
94d5e38c926fda232bb987b60fa9145e4bcf01a7. No dependency on PR95 or the historical-source
candidate. Only two ordinary test files and verification/process documents changed.
Production application, policies, contracts, and shared conftest remain byte-identical.
No restricted historical-integrity verification was retried or included.

Intent review: the two ctx fixtures drive authorized report generation, template/language,
review, audit roundtrip, export, missing-resource, rollback, GISIS and snapshot behavior.
Investigator's default medical Deny/applicable field policy prevents reaching that intended
business behavior. Those fixtures now explicitly use LeadInvestigator under the existing
policy. Exact before/after values, audit chain, hashes, cross-case and rollback assertions
are preserved. The old claim both investigator roles may read snapshots was corrected to
assert Lead allowed / default Investigator 403. Separate new tests require Investigator
403 for create/list/get/existence lookup/review/regenerate/export/audit/snapshot, no database
change, and denial before absent snapshot discovery for demo and public case identifiers.
Existing other-role denials remain unchanged. These are synthetic test principals, NOT SSO.

Actual ordinary-function verification:
- Before changes, two files: 58 failed, 9 passed in 15.53s on exact main. Failure IDs and
  raw-log SHA retained in baseline-summary.txt; raw local log is /tmp/report-functional-policy-baseline.txt.
- Candidate same two files plus two new denial tests: 69 passed in 18.74s (functional.txt).
  These call actual handlers/SQLite transactions, not external HTTP transport or browser.

HFACS remains separate. Parent's independent isolated export reported missing mcis-hfacs.sh
and 503. This complete checkout DOES have tools/mcis-hfacs/mcis-hfacs.sh; read-only checks
found no configured/default dotnet file, no dotnet on PATH, and no output mcis-hfacs.dll.
No shell/core invocation, SDK installation/download, HFACS test run or fake output in this
slice. The prior single HFACS failing test was not included, skipped as success, or fixed.
Do not claim the entire historical 59-failure group or full repository now passes.

No historical-candidate integration claim, real model, real browser, production identity,
performance, deployment or merge. Independent acceptance pending; local commit only.

Unchanged main test_reports_w162_access.py: 80 passed in 13.21s (access.txt). This is existing
policy/role/transaction HTTP regression on main, not historical-source integrity testing.
Its explicit fault-injection mocks remain test-only. Total selected checks across the two
runs: 149 passed, not a whole-suite result. No new test skips/xfails.
