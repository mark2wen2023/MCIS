# Protected trial issue archive HTTP

Added exact export/import/list/history paths to explicit identity trial app. The
export is raw UTF-8 JSON bytes with fixed safe attachment name; import sends only
inactive receipt summary. Input8MiB and response8MiB+small envelope budgets, actual
chunk accounting, deadline and no-store/nosniff. Cookie/Origin/encoding/old role
headers rejected; before-body authority and transactional service recheck remain.
No automatic initialization, credentials, grants, active history or legacy routes.

First completed prior budget-hardening regression:179/179 zero skipped, covering
issue domain/archive/HTTP, identity/catalog and prior demonstration service tests.
New primary HTTP tests:16/16. Their first invocation had an omitted imported
fixture; corrected test wiring, not a product failure. Final independent and
combined frozen results are recorded with acceptance report after completion.

Cancellation during receive does not mutate. A lost response after synchronous
restore can mean committed history; same-bundle retry confirms without duplicates.
An import receipt never claims restored active credentials or approved evidence.
No merge/deploy/browser UI/production login added.
Final independent HTTP suite:16 primary +20 independent =36/36 passed, zero skips.
ASGI/local SQLite tests, not browser/network/production authentication acceptance.
Independent report:tests_acceptance/ISSUE_ARCHIVE_HTTP/REPORT.md.
Final frozen combined related regression:215/215 passed, zero skips,116.17seconds.
Includes these36 tests plus earlier journal/archive/identity/catalog/demo-service
coverage; counts overlap and must not be added. Real W2 enabled where existing
tests exercise it; archive itself uses no LLM or W2. Not a repository-wide CI claim.
