# Investigation issue HTTP slice

Added four bounded issue routes to the explicit local-identity trial adapter:
creation, append-only event, historical read and summary listing. Server-owned
session and case/content authority are checked before request-body consumption;
writes require the separate issue grant. Business operations repeat authorization
inside their transaction. No provisioning route, legacy-role trust, auto-schema
initialization, browser identity bridge or deployment was added.

Independent review reproduced a namespace dispatch bug: a case ID beginning with
`issues` incorrectly shadowed its existing source catalog. Fixed namespace detection
to the complete `/cases/{case}/issues` path segment; regression retained. Default
protected entry remains closed and existing legacy app unchanged.

Actual local HTTP-adapter tests use ASGI in-process transport and real SQLite
business persistence; not real browser clicks, a listening network server,
production identity or LLM generation. Existing archive/restore does not include
journal records. Working notes never mean approved findings or verified facts.

Final exact test totals are recorded in tests_acceptance/ISSUE_HTTP/REPORT.md.

Independent final acceptance: 21 independent + 16 primary = 37 passed, zero skips.
Combined service regression: 150 passed, zero skips (includes those37; not additive),
covering journal domain, issue HTTP, existing identity HTTP/catalog and loopback demo
service tests with real W2 enabled for relevant existing tests. Existing
Starlette/httpx warning remains. Not a full-repository/448-suite or CI claim.
