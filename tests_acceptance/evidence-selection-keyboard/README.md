# EvidenceSelectionButton — synthetic keyboard acceptance

Production baseline: `ceea6e2a990720a5b57c3afc354c7dee6ee4a03b`.
This fixture directly imports its real `EvidenceSelectionButton.tsx` (SHA-256
`bd90e06ab248d0feccae3a47dae4c26419d3e148e16132b5530ff2e91f6457b4`).
It does not import EvidencePage, app/router, API, backend, seeds or legacy W42
runners. Two synthetic evidence IDs share one title. Local React state counts
selection and accidental parent click bubbling. No files are registered or read;
only disposable build/test artifacts are written.

## Existing dependencies only

Use the checkout's existing web Node/esbuild/React dependencies, Python 3 and,
for the optional actual browser run, an already installed Python Playwright plus
a compatible Chromium executable. No install, download or fallback is performed.
A normal supported Chromium sandbox must work. The known cloud host with the
nobody-owned setuid helper is not eligible; do not retry it, change permissions,
or add `--no-sandbox`. File navigation must be permitted by the host.

Build only, from repository root (output must not exist):

```sh
python tests_acceptance/evidence-selection-keyboard/build.py --output /tmp/selection-fixture-new.html
bash web/tests/run-evidence-intake-w42.sh
```

On an eligible host only, with a new disposable output directory:

```sh
python tests_acceptance/evidence-selection-keyboard/browser.py \
  --browser /absolute/path/to/approved/chromium \
  --output-dir /tmp/selection-keyboard-new
```

No listener is started. The runner builds a self-contained file and opens its
local file URI, with `chromium_sandbox=True` and no custom launch switches. It
blocks HTTP(S) requests and fails if one occurs. It never invokes a legacy runner.
Each width (1440 and 390, height 900) gets a fresh desktop/non-touch context.
The runner uses actual keyboard Tab/Shift+Tab, Enter and Space, not JS click or
forced focus: start → A → B → Enter → A → Space → end. Names include distinct
IDs; pressed state must switch; Tab alone selects nothing; activation calls
exactly once each; no row bubbling. These are component checks, not full product
view, source validity, actual account/permission, screen-reader or touch tests.

## Receipt and current evidence

`receipt.json` (also stdout) uses schema `mcis-selection-keyboard-v1`:
`baseline`, `componentSha256`, `harnessSha256` (three source files), `fixture`
(bytes/SHA/component SHA), `browserVersion`, `viewports`, `status`, `errorClass`,
`exitCode`. Each completed viewport records width/height/touch=false, status,
finite check names and screenshot SHA-256. Partial failure retains completed
viewports but overall fails and exits 1. Input/argument/output-directory errors
can exit before a receipt exists; absence is not success. `passed` requires both
viewports and normal browser teardown. Screenshots are local artifacts only.

In the authoring environment: build succeeded, generated HTML was parsed and its
inline JS syntax checked, Python syntax checked, and original W4.2 94 assertions
passed. No browser launch was attempted, so no browser receipt/screenshots or
keyboard pass is claimed. The generated HTML hash depends on installed build
versions and is recorded per run; the production component byte pin is mandatory.
The build rejects an existing output and unexpected source imports. First local
build rejected the existing node_modules symlink; checking resolved dependency
paths fixed that without allowing other product modules.
