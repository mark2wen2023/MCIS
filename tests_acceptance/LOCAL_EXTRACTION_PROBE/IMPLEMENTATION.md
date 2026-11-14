# Explicit local extraction probe (not real-model acceptance)

`python -m mcis_service.agents.local_extraction_probe` defaults to JSON `not_connected`, endpointConfigured=false, requestAttempted=false and exit 0. It does not read model environment variables, probe ports, download models, start services, or fall back to a fixture provider.

A trusted operator may explicitly provide **both** `--base-url` and `--model` for an already running selected loopback HTTP `/v1` model endpoint. There is no API key option, arbitrary case/path input, or production login. The host creates a temporary SQLite case and fixed fictional interview, one internal short-lived session and case membership with save permission disabled, then obtains a protected binding and calls the existing LocalProvider/host_extraction pipeline. It creates no proposal/review persistence grants and does not save the extracted proposals. Temporary resources are removed on ordinary exit; no claim of SIGKILL cleanup is made.

A successful response means the configured endpoint returned content that passed protected extraction and exact-quote checks. Output is only a sanitized summary/counts/checksum: configured model is a declaration and modelIdentityVerified remains false. Empty model proposals are valid protocol output, not evidence of useful extraction quality. The checksum is not a signature or durable audit. No prompt, internal token, raw endpoint error or model output is printed. On pipeline failure, requestAttempted is null when network egress cannot be determined, not an unsupported claim that HTTP occurred. Nonzero exit indicates invalid/unconfirmed; default not_connected is deliberately successful no-op.

## Transport hardening

Shared `model_client.validate_config` is now applied at `complete` entry before constructing httpx and by LocalProvider. Exact ModelConfig/string types; literal 127.0.0.1 or ::1 only, HTTP, explicit valid port, exact /v1 or /v1/ path. Reject URL whitespace/control/backslash, userinfo including empty `@`, query/fragment including empty `?`/`#`, invalid/blank model. Existing environment-based config() uses the same validator, while this probe never consults it. Existing httpx no-proxy/no-redirect/single-request bounded response behavior remains.

Independent review identified two real gaps: direct ModelConfig construction previously bypassed config() validation; empty URL delimiter/userinfo checks previously passed truthiness tests and could change path concatenation. Both are fixed before network client creation.

## Evidence and limits

The actual no-argument subprocess was run and returned not_connected. Successful and failing endpoint tests use mocked transport only; they are contract/security verification, **not real LLM inference or quality acceptance**. No endpoint was probed. The parent separately reported no explicitly configured local runtime available; no real-model run is claimed here.

Final candidate hashes:
- local_extraction_probe.py: 76631dd58139841bd7a59de11512a51f87c314fd72f4ce166385af37a0c8b0cd
- host_extraction.py: 561ccd86e0681b5d4a0cdb766808f9cbdd070ebe89e0adeecf35a0d9255f1178
- model_client.py: 81718af99f5424c86bd43daed40131a39318b3decab36e0427eee54b0219e63b

No push, merge or deployment by this worker.

Final combined regression: `test_local_extraction_probe.py`, `test_local_model_catalog_review.py`, `test_host_extraction.py`, `test_agents_w20.py`: **99 passed, 0 skipped**, 26.77 seconds. One pre-existing Starlette/httpx deprecation warning. This includes direct-transport configuration rejection and empty-delimiter regressions, not a real local model response.
