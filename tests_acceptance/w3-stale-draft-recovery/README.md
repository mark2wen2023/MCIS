# W3 protected trial: draft recovery after a definite conflict

Fixed baseline: MCIS `9a72cf3edaf420eddce393ce31d60d9c6b5fba34`.
This is the protected, opt-in IssueWorkspace trial, not the legacy or deployed
workbench. The separate `d4452bb` transcript-locator candidate is unchanged.

The journal already rejects stale expected revisions with an explicit 409.
Previously the TS host port discarded the protected response classification,
so the view treated it as an unknown transport failure and offered only an
identical, stale operation retry. Accept only the existing scope- and
request-bound `ISSUE_HOST_REJECTED` 409 for a save as definite rejection.
Unmatched/malformed responses still require the original retry procedure.
No change to HTTP/IPC contract, route, policy, evidence bytes, DB or credentials.

After rejection the component hides old historical display and source choices,
keeps the unsubmitted text, and requires an authorized re-read. For an unchanged
judgment it may continue editing, but a draft that originally had a citation
must reselect a current source before a new manual submit. If the judgment
changed, the old draft is never rebound: discard it and read again. Saved events
remain working, unreviewed. No shared hypothesis grouping, production mounting,
actual browser or provider is claimed. This does not persist unsaved text across
closing the component, and does not treat reopening saved records as fact review.

## Local synthetic validation

Use a candidate MCIS checkout and existing dependencies. No listener or install:

```sh
MCIS_NODE_MODULES=/existing/web/node_modules \
MCIS_HOST_PYTHON=/existing/service/.venv/bin/python \
MCIS_HAPPY_DOM_PATH=/existing/happy-dom/lib/index.js \
node tests_acceptance/w3-stale-draft-recovery/run.cjs
```

The runner builds in a temporary dir. It uses the real protected host callback
through stdio and authenticated in-process ASGI on a temporary SQLite DB. Test
controls append independent actual journal entries or dispose/reopen SQLite;
no source mutation or test control is mounted in the product.

24 assertions: baseline fails at definite 409 recovery; candidate passes.
Two separate cards cover advancing the revision under the same judgment,
changing the judgment, stale selection cleared, explicit reselection, wrong
request receipt still uncertain, deliberate recovery, and persisted SQLite
reopen with independent card histories. Existing source-version integration
also passed 32 assertions. React/HappyDOM is not a real browser.
