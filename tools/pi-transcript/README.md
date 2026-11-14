# MCIS Pi transcript runtime trial

This is an **actual Pi Agent 1.5.2 loop**, not a new name for a single completion.
It is an isolated trusted-host prototype, not mounted in the production workbench.
The default `mode: fixture` uses a simulated model. Explicit `remote-deepseek`
requires the bound adapter and approved Python remote host. See the remote
acceptance report for actual model results; mocked tests alone are not live proof. The existing
Python single-completion DeepSeek API remains unchanged and rejects tool calls.

## Run

Node >=22.19.0. From this directory:

```
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run test:integration
```

The integration uses `../../service/.venv/bin/python` and the repository service
by default. Test-only `MCIS_TEST_PYTHON` / `MCIS_TEST_SERVICE` override locations
for isolated developer snapshots. It starts only the fixed fictional stdio
fixture, never an HTTP listener, user account or input file. Temporary SQLite is
cleaned on normal exit. The selected Python environment needs service requirements.

## Boundaries

`runner.mjs` imports the official core and exposes `runTranscript` to trusted host
code only. No generic CLI, shell/file tool, MCP discovery, provider discovery,
OAuth, telemetry exporter or automatic model choice. A caller-supplied `stream`
is privileged code, not a model/UI parameter. Fixture designation is contractual;
it is not a sandbox for a malicious adapter. The current test adapter is offline.
The agent uses explicit tools with strict schemas and sequential execution:
read a redacted transcript range, find literal passages, validate an extraction.
Python rechecks actual session/case/source/policy before and after these operations.
It independently enforces 4 model calls, 8 tools and 120 seconds. Node enforces the
same ceiling, bounded messages and maxTokens=4096 per supplied adapter invocation.
This is not a billing guarantee for an adapter that ignores options.

Final text must equal a successfully validated candidate; Python validates it
again and rechecks authority. Output is PendingReview, never a saved/approved fact.
No write tools exist. Exact matching proves quotation provenance, not truth.
Cancellation/deadlines suppress late results but cannot promise to terminate an
arbitrary noncooperating adapter's already-started work. The remote host owns the canonical transcript, tool-call IDs and actual tool
results; Node cannot submit arbitrary messages. Python enforces the total HTTP
deadline with asyncio cancellation. The launcher also terminates its child when
the runtime ends; bytes already sent cannot be recalled.

Trace contains event types/tool names only; it is not a durable/signed audit.
No UI or genuine browser acceptance, no production authentication, no real model
accuracy validation, no CI pass, merge or deployment is claimed.

## Dependency review

Package and lockfile pin Pi 1.5.2. Upstream moved from badlogic/pi-mono to
https://github.com/earendil-works/pi. MIT upstream licence:
https://github.com/earendil-works/pi/blob/v1.5.2/LICENSE .
88 locked packages declare MIT(39), Apache-2.0(36), BSD-3-Clause(11),
Unlicense(1), 0BSD(1); all registry.npmjs.org integrity-pinned. The lockfile is
not a completed vulnerability or signature audit. Install scripts are disabled
(including those in @google/genai and protobufjs).
Upstream Pi defaults to NOOP telemetry; no exporter is configured here.
Independent interception of fetch/net/tls/http/https/dns/dgram during imports
and Agent/createModels construction observed zero attempted networking over
100ms. This does not certify every SDK path or a caller-supplied provider.

Do not redistribute node_modules as a complete licensed binary bundle yet:
10 installed packages lack top-level licence files (4 Pi packages,
@aws-sdk/credential-provider-http, @aws-sdk/credential-provider-login,
@aws-sdk/nested-clients, data-uri-to-buffer, proxy-agent-negotiate,
standardwebhooks). Preserve/recover applicable upstream LICENSE/NOTICE before
such distribution. This repository commits source and lockfile, not those bundles.

## Explicit fixed public-report live acceptance

`node live-probe.mjs --approved-public-report` accepts a single first stdin JSON
object `{"apiKey":"..."}` from a trusted operator. Do not put credentials in
command arguments, files, logs, or repository. This flag asserts that the user
already authorized the fixed public YANGZE22 excerpt and official DeepSeek use;
it is not a human-click verification service and does not authorize other cases.
The source report text and excerpt SHA, unique offset and page are pinned.
It uses temporary fixture identity, not production login, and is explicitly a
report excerpt, NOT witness testimony. No environment key lookup or auto-start.

The three remote tools remain read-only. Python maintains complete canonical
wire history and compares each callId/name/argument tuple to the actual model
response. Final content must equal a previously validated proposal and model
final reply. All model/tool boundaries reauthorize the same case/source snapshot.
The old single-completion DeepSeek adapter is unchanged. Pi usage fields are
zero placeholders required by its message type; `usageMeasured:false` means they
are not measured usage/cost or proof of zero billing.
