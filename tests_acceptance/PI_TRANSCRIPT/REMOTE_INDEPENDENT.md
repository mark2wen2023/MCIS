# Remote Pi boundary: independent review (2026-11-14)

Scope: Node remote adapter, host-owned canonical conversation/tool calls, explicit approved-scope digest, bounded official DeepSeek transport, and fixed public-report probe startup. All model/HTTP tests below use simulated responses. Reviewer used no real API credential and made no model API requests.

## Finding and fix

The first synchronous transport enforced only per-I/O HTTP timeout plus deadline checks after each received chunk. Independent two-chunk reproduction (80 ms each, 100 ms total deadline) returned after 160 ms: the absolute deadline was not enforced. This blocked real-model acceptance.

Implementer replaced that path with AsyncClient inside asyncio.timeout(remaining), covering connection, headers and body reads. The independent test was adapted to an asynchronous stream with the same delays. It now returns HTTPException 504 before the second read completes and verifies stream/client context cleanup. The failed original behavior is not counted as passed.

## Final reruns

- Node primary/independent fixture and remote suites: **34/34**, zero skips. Remote independent suite adds 11 tests: wrong adapter/model binding, invalid message roles/content/finish/tool arguments/count, prompt-context non-forwarding, and prompt cancellation of a hung canonical host. Branded remote adapters cannot be mislabeled fixture mode.
- Python remote and transcript-host primary/independent suites: **77/77**, zero skips, 44.13 seconds. The 8 independent remote tests cover canonical tool-result order, duplicate invocation rejection without repeat execution, confidential quotation rejection, injected case identity, malformed/missing history, and the absolute-deadline regression. Earlier host independent tests rechecked as part of this run.
- Fixed public-report probe startup: missing approval flag returns exit2; a fake test key followed by EOF produces one ready disclosure and exit0, with no model_request sent. Key absent from stdout/stderr. Public source text hash and fixed excerpt checks execute in this path. Input is explicitly report excerpt, not actual witness interview.

## Boundary assessment

Node does not issue HTTP or pass arbitrary conversation text to Python. Python owns canonical initial prompt, assistant responses and actual authorized tool results; call IDs, names, arguments and order must match. Remote dispatch rechecks source/permission/scope around inference and tools. Destination fixed to official DeepSeek endpoint; no redirects or retries, TLS verification enabled with managed proxy settings retained. Final candidate must equal both validated candidate and terminal model content, remains PendingReview/saved=false, and is not a fact approval.

No remaining blocking defect identified in tested scope. This permits proceeding to the separately authorized bounded public-data live experiment, not a statement that it already passed. The approval digest is a trusted-host scope binding, not proof of a human click. WeakMap is configuration binding, not a sandbox against malicious code inside the same trusted process. Node cancellation prevents result delivery but cannot itself guarantee termination of arbitrary uncooperative injected host code; the production transport has its own absolute timeout. usageMeasured=false correctly disclaims the Pi zero placeholder usage values.

## Exclusions

No real model/API, real business accuracy, production browser authentication/UI, persistent audit, merge, deployment, full-repository CI or supply-chain vulnerability audit was verified by this reviewer. Existing dependency/license caveats remain in INDEPENDENT.md. Runtime transport is synchronous callable (internally asyncio.run); the public async probe correctly invokes host.dispatch via asyncio.to_thread.

## Reviewed hashes

- runner.mjs: ffb4d70a2f9d7ce28a9e6aa916b571581b6048448341837a44c530dc6ff017db
- deepseek-adapter.mjs: 758ca7dcc54e8387d2d9249f31d8ebb077887c9f9e313d2c5953aad29a849ca9
- pi_deepseek_transport.py: 8c4db8509c4b40f4b37432d1e7dfd3085722cf6768a52020588cd37d8b1489c3
- pi_transcript_remote.py: 8edf86df32abdfbcc33aa35ece35bc71e0f457c7604af71eb857f1a2671c1a89
- pi_remote_public_probe.py: 04aafba24dd5b862a2195efdf9606fef50dfa8cf6cbdc6e44b4da98797280634

## Subsequent strict compatibility retest

Non-stream provider tool calls may carry an `index` field. The adapter now permits this one optional field only when it is an actual integer equal to the call's zero-based position (0..7), then strips it before retaining canonical history. Unique call IDs remain authoritative; unknown fields remain rejected. Independent added tests check successful normalization without mutating input and rejection of boolean/float/string/null/negative/wrong-order indices and extra fields. No generalized permissive parsing was introduced.

Final remote primary + independent suites: **63/63**, zero skips, 17.18 s, including the absolute timeout regression. `strict_json` also rejects exponent overflow/nonfinite floats. This supersedes the transport hash above: **117fa57b201c812cc5fe69ba594413ce30db71fe96e708b9b5ac7603f5ef1ac5**.

The fixed `live-probe.mjs` launcher was statically checked: key received through stdin, forwarded through child stdin, never inserted into argv/environment/files. Child environment is restricted to PATH/LANG and managed proxy/CA entries. Child stderr is discarded and public output contains statuses, counts, tool names and source hashes, not model text or keys. Host errors use a fixed safe-code allowlist. Input-line size is validated only after readline materializes it, so this is a trusted local acceptance launcher, not an untrusted public-input service. Launcher hash: **3b2877378ce73b6d7ecc75a10eaf869a681a5d1c04a2579b50c2042728c71e32**.

These checks did not invoke a real model. Live acceptance outcomes must be recorded separately.
