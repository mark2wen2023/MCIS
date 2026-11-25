# W11 opt-in edge click to server-held excerpt (synthetic only)

Base acceptance: MCIS `ede98a39e31ed8a24837dac241966c9c3fac4eb6`.
Reuses the published standalone server association without modifying it; actual
ECFC Graph/EdgeSelection and validation model from d9187fe. The product seam is
already an explicit click and accepts a reader only for a verified saved view.
Existing graph context is still registered-metadata-only; no product files,
default permissions, graph format, archive, or 4A are changed.

The disposable FastAPI acceptance host registers one private, schema-hidden POST
only in the harness; the normal app does not have it. Input cap and exact
context shape accept no source ID/path/locator from the caller. It reuses the
current product role context, existing server-defined immutable single binding,
source transaction and Access. Synthetic original only, one case and one edge
per isolated trial, zero off-machine connections. .NET result is the named
existing synthetic fixture; actual Python graph save/current authority and
intake/custody/SQLite boundaries execute.

Use the existing verified fixed source exports and dependencies:
```sh
MCIS_FIXED_SERVICE=/fixed/service MCIS_FIXED_WEB=/fixed/web \
MCIS_W11_SYNTHETIC_ORIGINAL=/fixed/communication.txt \
MCIS_NODE_MODULES=/existing/web/node_modules \
MCIS_HOST_PYTHON=/existing/service/.venv/bin/python \
MCIS_HAPPY_DOM_PATH=/existing/happy-dom/lib/index.js \
bash tests_acceptance/w11-edge-host-optin/run.sh
```

Actual mounted ECFC component and through its explicit button only (not click
selection) to the local TestClient route in isolated SQLite; each request
reopens from disk. No browser network or real Chrome. Revision and revocation
are separate cases of the same pilot. Wrong edge/Public denied without Access,
one explicit source read gives exactly one Access and only T+109 recorded UTC
and locator. Edit/revocation deny future reads and the view drops prior data
on remount or a subsequent read. No unsolicited push-based revocation, no
causal finding and zero seek.

For an actual product candidate, separately approve the enablement and
revocation ownership and route/response admission, then inject the reader
only in the saved, source-acknowledged non-dirty ECFC page when this exact
pilot is opted in. The production route, authentication, .NET correctness,
real web browser, and live revocation notification were not tested.

## Normal-sandbox Chromium acceptance

Use the same fixed inputs, plus installed Chromium and installed Python
Playwright ≥1.48; choose a fresh absolute output directory for each run.
No runtime or dependency is downloaded.

```sh
MCIS_BROWSER_BIN=/existing/chromium \
MCIS_BROWSER_PYTHON=/existing/python-with-playwright \
MCIS_W11_BROWSER_OUT=/absolute/fresh-output \
bash tests_acceptance/w11-edge-host-optin/run.sh --browser
```

Bundles the same ECFC view and connects it over same-origin localhost to a
real per-trial Uvicorn/FastAPI service on the temporary SQLite store. No
production browser route is installed. App HTTP is restricted to that one
loopback origin; WebSocket and service workers are refused. Writes
`run.log`, `exit-code.txt` and (upon reaching the applicable checkpoints)
separate revision/revocation read and denied PNGs. The local run compiled the
bundle but exited 2 before opening Chromium: the system wrapper lacks its
browser payload. No browser selectors or screenshot outcomes claimed here.

## Portable fixed inputs (preferred)

Use the existing service Python, existing node modules and separate local
repositories or exports already available to the operator. No lazy fetch.

```sh
/existing/service-python -I -B tests_acceptance/w11-edge-host-optin/pinned.py \
  --repository /existing/MCIS --verify-only
```

Repeat `--repository` if the fixed source trees are split across local object
stores. Instead of Git, repeat `--source-dir /existing/fixed-export` with the
fixed inputs; the first matching path must be the expected bytes. The
runner checks 186 service/contract/fixture blobs and 3 ECFC UI blobs before
running the test. To run browser mode, replace `--verify-only` with `--browser`
and set the existing dependencies/output variables from the browser section
above (no Happy DOM needed); for preflight, drop both flags and set the
existing Happy DOM entry. The fixed source variables are set by the runner.
