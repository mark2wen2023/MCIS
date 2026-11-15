# MCIS Pi adapter spike (synthetic only, not production)

An isolated, replaceable seam around `@earendil-works/pi-agent-core` 1.5.2. It is not imported by MCIS. It pins Pi packages to 1.5.2 and uses an offline, deterministic scripted provider in `test.mjs`. **No real LLM is connected or evaluated.** Never supply real case material to this prototype.

Run from this directory (Node.js 24 used in verification):

```sh
npm ci --ignore-scripts
npm test
```

The trusted host injects a provider and an already authorized, immutable-copy, single-case synthetic snapshot. Pi gets exactly three registered tools: `read_report`, `read_evidence`, `submit_candidate`. Arguments and case scope are checked at the application boundary; sources return IDs and versions; candidate references must have been delivered in the same run. A candidate is merely a proposal requiring human review, never a final report or archive mutation. Calls have a count limit and cancellation can block dispatch; events contain operational metadata only. No shell, arbitrary filesystem, or network tool is registered. This alone does not sandbox JavaScript or a provider: injected code could access the host. Only the local scripted provider was tested.

The application, not Pi, must own authentication, case and source authorization, secure storage, review, and durable audit. The declarative `synthetic` flag and caller-supplied scope do not verify data classification or identity. No production connector, external provider, expert orchestration, report adoption, or production permissions are changed. Data passed into a future provider may be transmitted by it and needs a separately authorized architecture and deployment review. Treat source text as untrusted: prompt-injection defense and semantic citation validation are not provided. Version-delivery tracking is not proof the model understood or relied on a source.

The budget counts calls reaching the application hook, not invalid or unknown tool calls rejected earlier by Pi. A separate provider-call limit of `maxCalls + 1` bounds repeated invalid or unknown requests across model calls. A response with more than `maxCalls` tool calls is rejected as a whole before dispatch, including unknown tools. Unknown or invalid calls across all responses can total up to `maxCalls × (maxCalls + 1)`, rather than `maxCalls`. This does not limit the response size before it is received. Neither limit bounds tokens, cost, inference duration, memory, or concurrent work. Parallel tool batches and cancellation of already-started work are not tested. Pi may coerce schema arguments, so production boundaries must independently perform strict validation. The cancellation test covers cancellation before tool body; no claim is made for interrupting an already running external operation or a non-cooperative provider. Event records are in-memory and not tamper-evident; tool results and candidate text are retained in returned messages. This is not production observability or security. A production integration must enforce authorization and cancellation at each backend operation, independently of the model or adapter.

## Verification

`node test.mjs` exercises allowed synthetic report/evidence reads, source version delivery, candidate creation, cross-case denial, missing source, unread/mismatched version, malformed argument, unknown shell, one-call budget, and cancellation before execution. It does not exercise real model quality or network isolation. This spike intentionally leaves the four-role expert workflow to the business layer; 海青君 is the host, with four independent reviews before cross-examination.
