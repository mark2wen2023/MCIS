# W19: keep the offline template tied to its current source

Product baseline `d0c4d8c2a6f2aaeee5e49b2085d4f744a491d642`; old
KnowledgePage Git blob `3cf927d55d988f8b83558d092498bbb7ab3d0fca`.
Existing template endpoint is PR54 source-backed deterministic preview
(`d356e66`); pinned suggestion adapter blob
`ab2edc8cb52411f5c57194d4e2a1d3ec7c4b1006`. No service changes.

After applying a template, an edit of the source fields or card type marks
the copied form stale. Merely restoring the old characters does not reset
that state: the investigator may apply a fresh preview for the current
source, or choose the clearly labeled reset retaining current source but
clearing title/body/summary/tags/applicability for manual writing. No silent
overwrite, save or publishing. Manual draft entry still works; this is a UI
guard, not a new source-certification guarantee or API permission change.

```sh
MCIS_NODE_MODULES=/existing/web/node_modules \
MCIS_HOST_PYTHON=/existing/service/.venv/bin/python \
MCIS_HAPPY_DOM_PATH=/existing/happy-dom/lib/index.js \
node tests_acceptance/w19-template-source-drift/run.cjs
```

Candidate passes ten actual mounted React actions through existing template,
create and exact read endpoints (real FastAPI/TestClient and temporary
SQLite). Exact old page fails at the first source-drift assertion.
Two deterministic previews and one intentional card create, no writes on
stale submit, exactly one audit action and public denial. After SQLite
reopen, the actual app ID reader displays the new source and stable digest.
No real browser/AI model, provider credentials, retrieval/training/publication
or production identity. No modifications to API, evidence, model or policy.
