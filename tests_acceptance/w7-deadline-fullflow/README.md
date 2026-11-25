# W7 deadline provenance through the actual recommendation page

Existing-scope synthetic acceptance. It checks the optional new-recommendation body, server-default 30 days and explicitly declared 45 days, local round/recommendation closure and audit after SQLite close/reopen. The old product incorrectly serializes days:30 as an explicit request; an untouched 590e0da tree should fail the candidate pin check. This package assumes the isolated two-file deadline integration on that base; it does not introduce or exercise an existing-editor feature.

Use already-installed Node, esbuild, MCIS web dependencies, Happy DOM, and a Python interpreter with existing MCIS service test dependencies. No install/download; no actual audio, model, real case, browser or production identity.

    node tests_acceptance/w7-deadline-fullflow/run.cjs \
      --repo /absolute/path/to/verified-candidate-checkout \
      --python /absolute/path/to/existing/venv/bin/python \
      --happy-dom /absolute/path/to/existing/happy-dom/lib/index.js

You may supply --node-modules /absolute/path/to/existing/web/node_modules if dependencies are external to the checkout. Dependency choices are operator-provided, not fetched; the fixed lockfile and 201 local product SHA-1 Git blobs are checked. The source tree may be materialized without .git; the runner does not write to it. It bundles into a fresh temporary directory alongside an empty SQLite store and removes both afterward. The bridge allowlists the one synthetic case and forwards real UI requests to actual FastAPI handlers. No outbound sockets, real users, browser or mocked API responses. It recreates the service against the same database to verify exact text, closed rounds, default/declared audit provenance, and an intact audit chain.

Dependency resolution uses the candidate's scoped web source and existing modules; a successful run does not close the full W7 package or cover formal source backlinking, authentication, browser, 428 compatibility, or external sending.
