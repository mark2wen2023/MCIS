# W19 exact re-open through current read authority

Fixed candidate baseline: MCIS `87ac70ec9ea87370a847446440aafe842746f027`
(product source follows `7ba7970ba4f77ebce11463d663e0f02a6c3f7928`).
The existing knowledge page already supports reviewing an internal candidate,
but the operator previously had to find it again via a different status filter.
An internal reader can now enter the exact server-issued card ID to re-open its
current saved record via the existing guarded detail GET. The read-only result
shows its exact digest, source text/locator and review note, and distinguishes
internal Candidate, currently published, and non-published states. Reopening
does not approve evidence, publish, alter status or authorize public reuse.
Only the separate existing review form can mutate a card.

The exact reader verifies IDs before requesting and refuses mismatched returned
IDs. Starting another request or editing its input hides previous content.
Unmount, identity changes, navigation and the existing write lock clear the
reader or suppress stale responses. Input and results are not persisted in the
browser. No new route, role, source access, status or review mechanism is added.

## Synthetic local acceptance

```sh
MCIS_NODE_MODULES=/existing/web/node_modules \
MCIS_HOST_PYTHON=/existing/service/.venv/bin/python \
MCIS_HAPPY_DOM_PATH=/existing/happy-dom/lib/index.js \
node tests_acceptance/w19-exact-card-reopen/run.cjs
```

Actual KnowledgePage UI/HappyDOM → existing API client → local stdio → real
FastAPI/TestClient and SQLite. Writes are the actual API, not an injected UI
success. The internal Candidate is saved with original source and digest,
published only through actual review controls and all three approvals, and
reopened after SQLite reconnect and component remount. Wrong response ID,
missing ID, and late reply after access changes show no stale source text.
An independently submitted real Withdrawn transition is re-read as not
published. The backend checks one card, three separate audit actions and a
valid chain, and Candidate/Withdrawn data stay unavailable to Public.

20 joined assertions pass twice. Baseline fails because the exact reopen entry
is missing. Existing React parser/read lifecycle 35 and backend API lifecycle 49
also pass. Happy DOM is not a real browser. Authority uses the existing local
demo role context, not production login. No model, provider, network listener,
source-artifact modifications, remote CI, merge or deployment.
