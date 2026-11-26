# W21 fixed-input replay preparation

Preparation only. Product repositories remain unchanged. The script checks
byte-identical synthetic fixtures from both commits and generates a separate
runner. It does not start servers or browsers, fetch dependencies, or assert a
browser/network result.

Use already available detached checkouts. Verify their exact HEAD before
starting any application:
- MCIS: `2048c60fd6650c6f2c99a76a16be463a3895655d`
- mcis-3d: `de9356a4616c0ef593ffff0ca81fd959ff24c1b3`

```sh
python prepare.py \
  --source "$MCIS3D/scripts/verify-cross-repo-replay.mjs" \
  --mcis-fixtures "$MCIS/tests_acceptance/shared-trajectory-cross-repo-expanded" \
  --mcis3d-fixtures "$MCIS3D/tests/fixtures/mcis-cross-repo-2048c60f" \
  --out "$PREP"
node --check "$PREP/verify-first-app-navigation.mjs"
```

The only change starts the CLI session at `about:blank`, so the existing page
request listener precedes the first application navigation. This measures page
requests, not all background browser traffic. Scope these separately. Use a
normal sandboxed Chrome and an already provisioned Playwright CLI; verify the
effective launch configuration. If it cannot start with the sandbox, stop and
record the blocker. Use only a loopback app and synthetic inputs; cloud accounts
and external tiles are outside this run. Once an authorized local runner is
ready, run from the pinned mcis-3d checkout:

```sh
node "$PREP/verify-first-app-navigation.mjs" --url http://127.0.0.1:3000 \
  --preset mcis-2048c60f --out-dir "$REPLAY_OUT"
```

Use new empty output directories. Record versions, command, exit status, raw
JSON/JSONL, PNGs, request scope and SHA256SUMS, keyed to the fixed revisions.
Do not describe these as recovered legacy originals.

Local preflight: six fixture blobs read from Git checked against both commits;
original runner verified; derived Node syntax passed. Deliberately changing one
fixture byte or one original runner byte rejected before creating output.
