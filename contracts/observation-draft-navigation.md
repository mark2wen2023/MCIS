# Observation draft navigation — candidate

Scope: existing observation text editor only. No server contract, permission,
receipt, automatic retry, persistence or source-access changes. Drafts remain in
page memory. A draft is dirty when its text differs from the last loaded or
contract-validated saved text. Failed/unknown responses do not clear that state.
An explicit refresh retains input while updating the comparison baseline.

The existing route table now uses React Router data hash routing, required by
useBlocker. Pending observation drafts trigger generic leave confirmation on
router navigation (including case query changes and history navigation). Cancel
keeps the current page; proceed allows disposal. beforeunload requests the
browser's native warning for reload/close. Browser policy may suppress it.
Leaving does not cancel an already dispatched request. The guard stores only
predicates, not text or identifiers, and sends nothing over the network.

Identity switching is not router navigation and is NOT guarded. A visible notice
states that limitation. This is not refresh recovery, durable drafts, or a guard
for other editors. No permission or production restore protections change.

## Developer validation

Base: d6dd764526a98a0fb02bbe0e9846d92f591ee543; independent local branch.

- observation-receipt-editor: 162 synthetic controller/SSR assertions, including
  long Unicode text after 412, 409, 500, network error, expiry, invalid success;
  successful save and explicit refresh baseline behavior.
- observation-navigation-guard: 16 assertions against installed real memory
  router and synthetic beforeunload events: cancel/proceed/back/case-change,
  multiple registrations and cleanup. Does not render native confirm or DOM.
- conflict-drafts: 15 existing assertions; case-context: 30 assertions.
- service/tests/test_observation_receipt_http_integration.py: 2 passed (1.06s),
  actual loopback HTTP with synthetic cases, not authenticated production identity.
- npm run build passed (773 modules); existing chunk-size warning remains.

Commands from web: bundle each tests/<name>.test.ts[x] with installed esbuild
--bundle --platform=node --format=cjs (SSR test adds --jsx=automatic), then node
its /tmp output. Backend: cd service && PYTHONPATH=.. .venv/bin/pytest -q
 tests/test_observation_receipt_http_integration.py.

No real browser validation. Native dialogs, actual hash-history/case switching,
React guard effect and all-route compatibility still require independent browser
acceptance. Prior blocked browser/security tests were not retried. No real model,
original evidence, credentials, merge or deployment involved. Assertion counts
are not pytest test counts and are not a full-system acceptance result.
