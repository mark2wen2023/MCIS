# Independent registered-preview UI checks

`registered-independent.tsx` executes 23 assertions: request ID/mapping boundary,
response case/source/approval checks, React cancellation and late responses,
case/identity/source-path invalidation, valid rendering, and parsing a captured
real-HTTP/W2 response plus tampered variants. It uses **HappyDOM and controlled
fetch**, not an actual browser or end-to-end UI/backend session.

`registered-independent.fixture.json` is the captured response from a local
uvicorn + actual W2 call using **fictional** 45/50-degree CSV inputs. It contains
no live credentials. Loading this fixture does not rerun HTTP or W2.

Prerequisites: install normal web dependencies, then the separate pinned test dependencies:

```sh
npm install --prefix web/tests/registered-acceptance
npm test --prefix web/tests/registered-acceptance
```

The independent package pins HappyDOM **21.0.4**. Its runner uses NODE_PATH to
resolve the separate test dependency, leaving the production package unchanged.

The emitted test file must remain beside the fixture (relative URL resolution).
Do not commit the emitted `.tmp-registered-independent.mjs` bundle. The runner
explicitly exits after all awaited assertions and component unmount, because the
DOM emulator can retain asynchronous handles. This is not a service shutdown test.

Independent execution used existing installed HappyDOM 21.0.4 and project React/
esbuild dependencies. All 23 checks passed. Production sources were not changed
by the reviewer. Real browser visual/layout validation remains pending.

The scoped-workbench update additionally checks echoed declarations, missing/dishonest scope statuses and invalidation after a declaration handler change. The in-flight change is a synthetic event against a disabled field to exercise the handler, not a real browser action.
