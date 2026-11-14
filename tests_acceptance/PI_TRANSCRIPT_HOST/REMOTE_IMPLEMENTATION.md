# Remote Pi host and transport implementation scope

Separate `pi_deepseek_transport.py`, `pi_transcript_remote.py` and fixed
`pi_remote_public_probe.py`. Original single-shot DeepSeek transport unchanged
(SHA256 26bd4d0cf096c7da6acd4daf858945a14b70f0b86e408d758c8007639b16fed2).

Host owns canonical messages, fixed prompt/tools and approved source/model scope.
Caller cannot supply messages or provider settings through protocol. Each actual
model tool call ID/name/arguments must match the next real execution; results are
appended by the host, and incomplete results block further inference. A final
response must equal model terminal content and previously validated content, with
at least one source-read/search action. Final is PendingReview only, not saved.

Transport: fixed official HTTPS; managed proxy/CA with TLS verification; no
redirect/retry; tool allowlist; strict duplicate JSON keys/finite numbers; response
and request byte bounds. True total deadline uses asyncio.timeout around
AsyncClient connect/headers/body, not just per-read timeouts. Slow-drip test checks
cancellation and resource closure. Sync callable must run outside an active event
loop; provided async probe invokes it using asyncio.to_thread.

Fixed public probe requires `--approved-public-report` and first stdin JSON
`{"apiKey":"..."}`. Key is held only in memory, never argv or files. This explicit
trusted caller selection asserts prior authorization of the fixed public-report
scope; it is not a browser consent interaction or verified human-approval receipt.
It checks the full report.txt SHA, exact unique excerpt SHA and offset5987. Source:
https://www.sh.msa.gov.cn/sgdc/104170.jhtml, printed page1/PDF page3. This is a
public-report excerpt, not a witness interview; source storage uses a temporary
fixture identity/record adapter, not production login or original-evidence intake.
Ready contains exact disclosure/source metadata; then normal protocol. Rejection
returns only allowlisted errorCode, never arbitrary exception detail/content.

All remote transport/model results in primary tests are MOCKED. Real SQLite and
Python subprocess tests do not prove genuine model or Pi-runtime operation.
No real API called by this implementer. Parent owns independent review and live
Pi/DeepSeek integration. No commit, merge, deployment or CI claimed here.

Final primary regression (2026-11-14):
`python -m pytest tests/test_pi_remote.py tests/test_pi_transcript_host.py tests/test_host_extraction.py tests/test_deepseek_client.py -q`
**108 passed, zero skips, 41.95s**, existing Starlette/httpx deprecation warning.
33 remote/mock checks +29 read-only host checks +15 original host checks +31
original single-shot transport checks. No cross-suite summation with earlier runs.

Post-live-structure compatibility fix: accept optional non-stream tool-call `index`
only if exact nonboolean integer matching array position0..7; strip it before
canonical storage. Unknown metadata and malformed/duplicate indices still fail.
Focused final `tests/test_pi_remote.py`: **44 passed**, zero skips,14.11s.
Eleven new positional metadata checks; earlier108 combined run predates this fix.
No fresh real-model claim from this implementer; parent owns live runs.
